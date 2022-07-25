import base64
import json
from time import time

from ..exceptions.invalid_path_exception import InvalidPathException
from ...common.protocol.message_protocol import MessageProtocol
from ..exceptions.sdk_exception import OpenLISAException
from ..exceptions.invalid_command import InvalidCommandException
from ...logging import log

SUCCESS_RESPONSE = "OK"
ERROR_RESPONSE = "ERROR"

COMMAND_DISCONNECT = "DISCONNECT"
COMMAND_GET_INSTRUMENTS = "GET_INSTRUMENTS"
COMMAND_GET_INSTRUMENT = "GET_INSTRUMENT"
COMMAND_CREATE_INSTRUMENT = "CREATE_INSTRUMENT"
COMMAND_UPDATE_INSTRUMENT = "UPDATE_INSTRUMENT"
COMMAND_DELETE_INSTRUMENT = "DELETE_INSTRUMENT"
COMMAND_GET_INSTRUMENT_COMMANDS = "GET_INSTRUMENT_COMMANDS"
COMMAND_VALIDATE_COMMAND = "VALIDATE_COMMAND"
COMMAND_SEND_COMMAND = "SEND_COMMAND"
COMMAND_GET_FILE = "GET_FILE"
COMMAND_SEND_FILE = "SEND_FILE"
COMMAND_EXECUTE_BASH = "EXECUTE_BASH"
# Only available when server is running in test mode
COMMAND_RESET_DATABASES = "RESET_DATABASES"


class ClientProtocol:
    def __init__(self, message_protocol: MessageProtocol):
        self._message_protocol = message_protocol

    def __is_valid_response(self, response):
        if response == SUCCESS_RESPONSE:
            return True
        if response == ERROR_RESPONSE:
            return False

        raise Exception("unknown response type: '{}'".format(response))

    def disconnect(self):
        log.debug("[LATENCY_MEASURE][INIT][{}]".format('disconnect'))
        ts = time()
        self._message_protocol.send_msg(COMMAND_DISCONNECT)
        te = time()
        log.debug("[LATENCY_MEASURE][FINISH][{}][ELAPSED={} seconds]".format(
            'disconnect', te-ts))
        self._message_protocol.disconnect()
        return

    def create_instrument(self, new_instrument):
        return json.loads(self.get_instrument_as_json_string(new_instrument))

    def create_instrument_as_json_string(self, new_instrument):
        self._message_protocol.send_msg(COMMAND_CREATE_INSTRUMENT)
        self._message_protocol.send_msg(json.dumps(new_instrument))
        response_type = self._message_protocol.receive_msg()
        result_msg = self._message_protocol.receive_msg()
        if self.__is_valid_response(response_type):
            return result_msg
        else:
            raise OpenLISAException(result_msg)

    def update_instrument(self, id, updated_instrument):
        id = str(id)
        return json.loads(self.update_instrument_as_json_string(id, updated_instrument))

    def update_instrument_as_json_string(self, id, updated_instrument):
        id = str(id)
        self._message_protocol.send_msg(COMMAND_UPDATE_INSTRUMENT)
        self._message_protocol.send_msg(id)
        self._message_protocol.send_msg(json.dumps(updated_instrument))
        response_type = self._message_protocol.receive_msg()
        result_msg = self._message_protocol.receive_msg()
        if self.__is_valid_response(response_type):
            return result_msg
        else:
            raise OpenLISAException(result_msg)

    def delete_instrument(self, id):
        id = str(id)
        return json.loads(self.delete_instrument_as_json_string(id))

    def delete_instrument_as_json_string(self, id):
        id = str(id)
        self._message_protocol.send_msg(COMMAND_DELETE_INSTRUMENT)
        self._message_protocol.send_msg(id)
        response_type = self._message_protocol.receive_msg()
        result_msg = self._message_protocol.receive_msg()
        if self.__is_valid_response(response_type):
            return result_msg
        else:
            raise OpenLISAException(result_msg)

    def get_instruments(self):
        return json.loads(self.get_instruments_as_json_string())

    def get_instruments_as_json_string(self):
        log.debug("[LATENCY_MEASURE][INIT][{}]".format('get_instruments'))
        ts = time()
        self._message_protocol.send_msg(COMMAND_GET_INSTRUMENTS)
        result = self._message_protocol.receive_msg()
        te = time()
        log.debug("[LATENCY_MEASURE][FINISH][{}][ELAPSED={} seconds]".format(
            'get_instruments', te-ts))
        return result

    def get_instrument(self, id):
        id = str(id)
        return json.loads(self.get_instrument_as_json_string(id))

    def get_instrument_as_json_string(self, id):
        id = str(id)
        log.debug("[LATENCY_MEASURE][INIT][{}]".format('get_instrument'))
        ts = time()
        self._message_protocol.send_msg(COMMAND_GET_INSTRUMENT)
        self._message_protocol.send_msg(id)
        response_type = self._message_protocol.receive_msg()
        result_msg = self._message_protocol.receive_msg()
        te = time()
        log.debug("[LATENCY_MEASURE][FINISH][{}][ELAPSED={} seconds]".format(
            'get_instrument', te-ts))
        if self.__is_valid_response(response_type):
            return result_msg
        else:
            raise OpenLISAException(result_msg)

    def get_instrument_commands(self, id):
        return json.loads(self.get_instrument_commands_as_json_string(id))

    def get_instrument_commands_as_json_string(self, id):
        id = str(id)
        log.debug("[LATENCY_MEASURE][INIT][{}]".format(
            'get_instrument_commands'))
        ts = time()
        self._message_protocol.send_msg(COMMAND_GET_INSTRUMENT_COMMANDS)
        self._message_protocol.send_msg(id)
        response_type = self._message_protocol.receive_msg()
        result_msg = self._message_protocol.receive_msg()
        te = time()
        log.debug("[LATENCY_MEASURE][FINISH][{}][ELAPSED={} seconds]".format(
            'get_instrument_commands', te-ts))
        if self.__is_valid_response(response_type):
            return result_msg
        else:
            raise OpenLISAException(result_msg)

    def validate_command(self, id, command):
        id = str(id)
        log.debug("[LATENCY_MEASURE][INIT][{}]".format('validate_command'))
        ts = time()
        self._message_protocol.send_msg(COMMAND_VALIDATE_COMMAND)
        self._message_protocol.send_msg(id)
        self._message_protocol.send_msg(command)
        response_type = self._message_protocol.receive_msg()
        if not self.__is_valid_response(response_type):
            err = self._message_protocol.receive_msg()
            te = time()
            log.debug("[LATENCY_MEASURE][FINISH][{}][ELAPSED={} seconds]".format(
                'validate_command', te-ts))
            raise InvalidCommandException(
                "command '{}' is not valid: {}".format(command, err))

        te = time()
        log.debug("[LATENCY_MEASURE][FINISH][{}][ELAPSED={} seconds]".format(
            'validate_command', te-ts))

    def send_command(self, id, command, command_result_output_file):
        id = str(id)
        json_str = self.send_command_and_result_as_json_string(
            id, command, command_result_output_file)

        command_execution_result_dict = json.loads(json_str)
        command_execution_value = command_execution_result_dict["value"]
        command_execution_type = command_execution_result_dict["type"]

        if not command_execution_value:  # output value was saved in server
            return command_execution_result_dict

        # BYTES are sent as a base64 string
        if command_execution_type == "BYTES":
            command_execution_value = base64.b64decode(command_execution_value)
        return command_execution_result_dict

    def send_command_and_result_as_json_string(self, id, command, command_result_output_file):
        id = str(id)
        log.debug("[LATENCY_MEASURE][INIT][{}][command={}]".format(
            'send_command', command))
        ts = time()
        self._message_protocol.send_msg(COMMAND_SEND_COMMAND)
        command_execution_request = {
            "instrument_id": id,
            "command_invocation": command,
            "command_result_output_file": command_result_output_file
        }
        self._message_protocol.send_msg(json.dumps(command_execution_request))
        response_type = self._message_protocol.receive_msg()
        if self.__is_valid_response(response_type):
            command_execution_result_json_str = self._message_protocol.receive_msg()
            te = time()
            log.debug("[LATENCY_MEASURE][FINISH][{}][command={}][ELAPSED={} seconds]".format(
                'send_command', command, te-ts))

            return command_execution_result_json_str
        else:
            err = self._message_protocol.receive_msg()
            te = time()
            log.debug("[LATENCY_MEASURE][FINISH][{}][command={}][ELAPSED={} seconds]".format(
                'send_command', command, te-ts))
            raise InvalidCommandException(
                "command '{}' for instrument {} is not valid: {}".format(command, id, err))

    def send_file(self, file_bytes, file_target_name):
        log.debug("[LATENCY_MEASURE][INIT][{}]".format('send_file'))
        ts = time()
        self._message_protocol.send_msg(COMMAND_SEND_FILE)
        self._message_protocol.send_msg(file_target_name)
        self._message_protocol.send_msg(file_bytes, encode=False)

        response = self._message_protocol.receive_msg()
        if not self.__is_valid_response(response):
            err = self._message_protocol.receive_msg()
            te = time()
            log.debug("[LATENCY_MEASURE][FINISH][{}][ELAPSED={} seconds]".format(
                'send_file', te-ts))
            raise InvalidPathException(err)

        te = time()
        log.debug("[LATENCY_MEASURE][FINISH][{}][ELAPSED={} seconds]".format(
            'send_file', te - ts))

        return response

    def get_file(self, remote_file_name):
        log.debug("[LATENCY_MEASURE][INIT][{}]".format('get_file'))
        ts = time()
        self._message_protocol.send_msg(COMMAND_GET_FILE)
        self._message_protocol.send_msg(remote_file_name)
        response_type = str(self._message_protocol.receive_msg())

        if not self.__is_valid_response(response_type):
            error_message = self._message_protocol.receive_msg()
            log.error("Error requesting remote file '{}' : {}".format(
                remote_file_name, error_message))
            raise OpenLISAException(error_message)

        file_bytes = self._message_protocol.receive_msg(decode=False)

        te = time()
        log.debug("[LATENCY_MEASURE][FINISH][{}][ELAPSED={} seconds]".format(
            'get_file', te - ts))

        return file_bytes

    def execute_bash_command(self, command, capture_stdout, capture_stderr):
        log.debug("[LATENCY_MEASURE][INIT][{}]".format('execute_bash_command'))
        ts = time()
        stdout = None
        stderr = None
        self._message_protocol.send_msg(COMMAND_EXECUTE_BASH)
        self._message_protocol.send_msg(command)
        self._message_protocol.send_msg(str(capture_stdout))
        self._message_protocol.send_msg(str(capture_stderr))
        status_code = str(self._message_protocol.receive_msg())
        log.info(
            "Status code after remote bash command execution: {}".format(status_code))

        if capture_stdout:
            stdout = str(self._message_protocol.receive_msg())
            log.debug("Remote execution command stdout: {}".format(stdout))

        if capture_stderr:
            stderr = str(self._message_protocol.receive_msg())
            log.debug("Remote execution command stderr: {}".format(stderr))

        te = time()
        log.debug("[LATENCY_MEASURE][FINISH][{}][ELAPSED={} seconds]".format(
            'execute_bash_command', te - ts))

        return status_code, stdout, stderr

    def reset_databases(self):
        self._message_protocol.send_msg(COMMAND_RESET_DATABASES)
        return self._message_protocol.receive_msg()
