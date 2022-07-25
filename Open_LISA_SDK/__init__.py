import json
import socket
import traceback
import serial
import serial.tools.list_ports

from .domain.exceptions.invalid_command import InvalidCommandException

from .common.protocol.message_protocol_rs232 import MessageProtocolRS232
from .common.protocol.message_protocol_tcp import MessageProtocolTCP
from .domain.exceptions.sdk_exception import OpenLISAException

from .domain.protocol.client_protocol import ClientProtocol

from .domain.exceptions.could_not_connect_to_server import CouldNotConnectToServerException
from .logging import log

DEFAULT_RS232_BAUDRATE = 921600

SDK_RESPONSE_FORMAT_JSON = "JSON"
SDK_RESPONSE_FORMAT_PYTHON = "PYTHON"
SDK_VALID_RESPONSE_FORMATS = [
    SDK_RESPONSE_FORMAT_JSON, SDK_RESPONSE_FORMAT_PYTHON]

CONVERT_TO_STRING = "str"
CONVERT_TO_DOUBLE = "double"
CONVERT_TO_BYTEARRAY = "bytearray"
CONVERT_TO_BYTES = "bytes"
CONVERT_TO_INT = "int"

AVAILABLE_CONVERT_TYPES = [
    CONVERT_TO_STRING,
    CONVERT_TO_DOUBLE,
    CONVERT_TO_BYTEARRAY,
    CONVERT_TO_BYTES,
    CONVERT_TO_INT,
]


class SDK:
    def __init__(self, log_level="WARNING", default_response_format=SDK_RESPONSE_FORMAT_PYTHON):
        log.set_level(log_level)
        log.info("Initializating SDK")

        self._default_response_format = default_response_format

    def connect_through_TCP(self, host, port):
        try:
            server_address = (host, int(port))
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(server_address)
            self._client_protocol = ClientProtocol(MessageProtocolTCP(sock))
        except Exception as e:
            log.error(e)
            raise CouldNotConnectToServerException(
                "could not connect with server at {} through TCP".format(server_address))

    def connect_through_RS232(self, baudrate=DEFAULT_RS232_BAUDRATE, port=None):
        # Discover server RS232
        TIMEOUT_TO_WAIT_HANDSHAKE_RESPONSE = 3
        RS232_HANDSHAKE_CLIENT_REQUEST = 'OPEN'
        RS232_HANDSHAKE_SERVER_RESPONSE = 'LISA'

        connection = None
        detected_ports_info_instances = serial.tools.list_ports.comports()
        detected_port_devices = [
            pinfo.device for pinfo in detected_ports_info_instances]
        ports_to_try = detected_port_devices if not port else [port]
        for port in ports_to_try:
            try:
                log.debug(
                    '[connect_through_RS232] trying to connect to {}'.format(port))
                connection = serial.Serial(
                    port=port, baudrate=baudrate, timeout=TIMEOUT_TO_WAIT_HANDSHAKE_RESPONSE)
                log.debug(
                    '[connect_through_RS232] connection created {}'.format(connection))
                if not connection.is_open:
                    connection.open()

                # custom handshake
                MAX_UNSIGNED_INT = 4_294_967_295
                log.debug(
                    '[connect_through_RS232] setting buffer size to {}B'.format(4_294_967_295))
                connection.set_buffer_size(
                    rx_size=MAX_UNSIGNED_INT, tx_size=MAX_UNSIGNED_INT)
                connection.write(RS232_HANDSHAKE_CLIENT_REQUEST.encode())
                response = connection.read(
                    len(RS232_HANDSHAKE_SERVER_RESPONSE))
                if len(response) > 0 and str(response.decode()) == RS232_HANDSHAKE_SERVER_RESPONSE:
                    log.debug('Detect Open LISA server at {} with baudrate {}'.format(
                        port, baudrate))
                    break
                else:
                    connection = None
                    log.debug("no answer detected from {}".format(port))
            except serial.SerialException as ex:
                log.info('serial exception {}'.format(ex))
                log.debug('exception stacktrace {}'.format(
                    traceback.format_exc()))
                log.debug("could not connect to {}".format(port))
                connection = None

        if not connection:
            raise CouldNotConnectToServerException(
                "could not detect Open LISA server listening through RS232")

        self._client_protocol = ClientProtocol(
            MessageProtocolRS232(rs232_connection=connection))

    def disconnect(self):
        self._client_protocol.disconnect()

    def __reset_databases(self):
        return self._client_protocol.reset_databases()

    def create_instrument(self, new_instrument, response_format=None):
        created_instrument_as_json_string = self._client_protocol.create_instrument_as_json_string(
            new_instrument)
        return self.__format_response(created_instrument_as_json_string, response_format)

    def update_instrument(self, instrument_id, updated_instrument, response_format=None):
        updated_instrument_as_json_string = self._client_protocol.update_instrument_as_json_string(
            instrument_id, updated_instrument)
        return self.__format_response(updated_instrument_as_json_string, response_format)

    def delete_instrument(self, instrument_id, response_format=None):
        deleted_instrument = self._client_protocol.delete_instrument_as_json_string(
            instrument_id)
        return self.__format_response(deleted_instrument, response_format)

    def get_instruments(self, response_format=None):
        """
        Returns the list of instruments dictionaries
        """
        instruments_as_json_string = self._client_protocol.get_instruments_as_json_string()
        return self.__format_response(instruments_as_json_string, response_format)

    def get_instrument(self, instrument_id, response_format=None):
        """
        Returns the instrument with the ID specified, raises if not found
        """
        instrument_as_json_string = self._client_protocol.get_instrument_as_json_string(
            instrument_id)
        return self.__format_response(instrument_as_json_string, response_format)

    def get_instrument_commands(self, instrument_id, response_format=None):
        commands_as_json_string = self._client_protocol.get_instrument_commands_as_json_string(
            id=instrument_id)
        return self.__format_response(commands_as_json_string, response_format)

    def is_valid_command_invocation(self, instrument_id, command_invocation):
        try:
            self._client_protocol.validate_command(
                instrument_id, command_invocation)
            print("{} is OK".format(command_invocation))
            return True
        except InvalidCommandException as e:
            print(e)
            return False

    def send_command(self, instrument_id, command_invocation, command_result_output_file=None, response_format=None, convert_result_to=None):
        if response_format == SDK_RESPONSE_FORMAT_JSON or (
                response_format == None and self._default_response_format == SDK_RESPONSE_FORMAT_JSON):
            # If response format is json convert_result_to is ignored
            return self._client_protocol.send_command_and_result_as_json_string(instrument_id, command_invocation, command_result_output_file)

        command_execution_result = self._client_protocol.send_command(
            instrument_id, command_invocation, command_result_output_file)

        if not convert_result_to or command_result_output_file:
            return command_execution_result

        original_value = command_execution_result["value"]
        try:
            if convert_result_to == CONVERT_TO_STRING:
                command_execution_result["value"] = str(original_value)
            elif convert_result_to == CONVERT_TO_INT:
                command_execution_result["value"] = \
                    int(float((original_value)))
            elif convert_result_to == CONVERT_TO_DOUBLE:
                command_execution_result["value"] = float(original_value)
            elif convert_result_to == CONVERT_TO_BYTEARRAY:
                command_execution_result["value"] = bytearray(original_value)
            elif convert_result_to == CONVERT_TO_BYTES:
                command_execution_result["value"] = bytes(original_value)

        except ValueError as e:
            error = "could not convert '{}' to type '{}'.".format(
                original_value, convert_result_to)
            log.error(error)
            raise InvalidCommandException(error)

        return command_execution_result

    def send_file(self, file_path, file_target_name):
        with open(file_path, "rb") as file:
            data = file.read()
            return self._client_protocol.send_file(data, file_target_name)

    def get_file(self, remote_file_name, file_target_name):
        file_bytes = self._client_protocol.get_file(remote_file_name)
        with open(file_target_name, "wb") as file:
            file.write(file_bytes)

    def execute_bash_command(self, command, capture_stdout=False, capture_stderr=False):
        return self._client_protocol.execute_bash_command(command, capture_stdout, capture_stderr)

    def __format_response(self, json_string, response_format):
        response_format = response_format if response_format else self._default_response_format
        assert response_format in SDK_VALID_RESPONSE_FORMATS
        if response_format == SDK_RESPONSE_FORMAT_JSON:
            return json_string
        elif response_format == SDK_RESPONSE_FORMAT_PYTHON:
            return json.loads(json_string)
