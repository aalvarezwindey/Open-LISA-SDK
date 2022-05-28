import json
from functools import wraps
from time import time
from ..exceptions.sdk_exception import OpenLISAException
from ..exceptions.invalid_command import InvalidCommandException
from ...logging import log

# Source: https://stackoverflow.com/questions/1622943/timeit-versus-timing-decorator
def with_latency_logs(f):
  @wraps(f)
  def wrap(*args, **kw):
    entering(f)
    ts = time()
    result = f(*args, **kw)
    te = time()
    exiting(f, te-ts)
    return result
  return wrap

def entering(func):
	""" Pre function logging """
	log.debug("[LATENCY_MEASURE][INIT][{}]".format(func.__name__))

def exiting(func, elapsed):
	""" Post function logging """
	log.debug("[LATENCY_MEASURE][FINISH][{}][ELAPSED={.8f}]".format(func.__name__, elapsed))

SUCCESS_RESPONSE = "OK"
ERROR_RESPONSE = "ERROR"


COMMAND_GET_INSTRUMENTS = "GET_INSTRUMENTS"
COMMAND_GET_INSTRUMENT = "GET_INSTRUMENT"
COMMAND_GET_INSTRUMENT_COMMANDS = "GET_INSTRUMENT_COMMANDS"
COMMAND_VALIDATE_COMMAND = "VALIDATE_COMMAND"
COMMAND_SEND_COMMAND = "SEND_COMMAND"

class ClientProtocol:
  def __init__(self, message_protocol):
    self._message_protocol = message_protocol

  def __is_valid_response(self, response):
    if response == SUCCESS_RESPONSE:
      return True
    if response == ERROR_RESPONSE:
      return False

    raise Exception("unknown response type: '{}'".format(response))

  @with_latency_logs()
  def get_instruments(self):
    log.debug('')
    self._message_protocol.send_msg(COMMAND_GET_INSTRUMENTS)
    return json.loads(self._message_protocol.receive_msg())

  @with_latency_logs()
  def get_instrument(self, id):
    self._message_protocol.send_msg(COMMAND_GET_INSTRUMENT)
    self._message_protocol.send_msg(id)
    response_type = self._message_protocol.receive_msg()
    if self.__is_valid_response(response_type):
      return json.loads(self._message_protocol.receive_msg())
    else:
      raise OpenLISAException(self._message_protocol.receive_msg())

  @with_latency_logs()
  def get_instrument_commands(self, id):
    self._message_protocol.send_msg(COMMAND_GET_INSTRUMENT_COMMANDS)
    self._message_protocol.send_msg(id)
    response_type = self._message_protocol.receive_msg()
    if self.__is_valid_response(response_type):
      return json.loads(self._message_protocol.receive_msg())
    else:
      raise OpenLISAException(self._message_protocol.receive_msg())

  @with_latency_logs()
  def validate_command(self, id, command):
    self._message_protocol.send_msg(COMMAND_VALIDATE_COMMAND)
    self._message_protocol.send_msg(id)
    self._message_protocol.send_msg(command)
    response_type = self._message_protocol.receive_msg()
    if not self.__is_valid_response(response_type):
      err = self._message_protocol.receive_msg()
      raise InvalidCommandException("command '{}' is not valid: {}".format(command, err))

  @with_latency_logs()
  def send_command(self, id, command):
    self._message_protocol.send_msg(COMMAND_SEND_COMMAND)
    self._message_protocol.send_msg(id)
    self._message_protocol.send_msg(command)
    response_type = self._message_protocol.receive_msg()
    if self.__is_valid_response(response_type):
      format = self._message_protocol.receive_msg()
      response = self._message_protocol.receive_msg(decode=False)
      return format, response
    else:
      err = self._message_protocol.receive_msg()
      raise InvalidCommandException("command '{}' for instrument {} is not valid: {}".format(command, id, err))
