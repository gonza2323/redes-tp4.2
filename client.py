from prompt_toolkit import PromptSession, application
from prompt_toolkit.patch_stdout import patch_stdout
from common import *
import threading
import socket
import time


PORT = 60000
BUFFER_SIZE = 1024
MSG_PROMPT = "> "


class App:
    _username = None
    _app_state = None
    _client_socket = None
    _host = None
    _stop_app = None
    _stop_connection = None
    _session = None
    _read_messages_thread = None
    _prompt = {"prompt": ""}


    def __init__(self):
        self._app_state = "DISCONNECTED"
        self._stop_connection = threading.Event()
        self._stop_app = threading.Event()
        self._session = PromptSession()
    

    def start(self):
        try:
            self._username = get_username()
            while not self._stop_app.is_set():
                self._handle_user_input()

        except KeyboardInterrupt:
            self.stop()
        finally:
            self._stop_connection.set()
            self._stop_app.set()
            if self._client_socket:
                self._client_socket.close()
        

    def stop(self):
        self._stop_connection.set()
        self._stop_app.set()
        if self._client_socket:
            self._client_socket.close()
        print("Saliendo...")
        time.sleep(0.2)


    def _handle_user_input(self):
        user_input = self._session.prompt(self._get_prompt)

        match self._app_state:
            case "DISCONNECTED":
                if (user_input == 'exit'):
                    self.stop()
                    return
                
                if self._connect_to_host(user_input):
                    self._set_state("CONNECTED")
                                        
            case "CONNECTED":
                if (user_input == 'exit'):
                    self._set_state("DISCONNECTED")
                    return

                self._send_message(user_input)


    def _set_state(self, new_state):
        self._app_state = new_state
        
        match new_state:
            case "DISCONNECTED":
                self._stop_connection.set()
                self._host = None
                if self._client_socket:
                    self._client_socket.close()

            case "CONNECTED":
                self._stop_connection.clear()
                if not self._read_messages_thread:
                    self._read_messages_thread = threading.Thread(target=self._read_messages, daemon=True)
                    self._read_messages_thread.start()
        
        app = application.current.get_app()
        app.invalidate() # forzar la actualización del prompt

    
    def _connect_to_host(self, host):
        try:
            if (self._client_socket):
                self._client_socket.close()
            
            self._client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._client_socket.connect((host, PORT))
            
        except Exception as e:
            print(f"No se pudo conectar al host {host}:{PORT}. Error: ", e)
            return False
        
        self._host = host
        print(f"Conectado al host {host}:{PORT}")

        return True


    def _get_prompt(self):
        match self._app_state:
            case "DISCONNECTED":
                self._prompt["prompt"] = "Ingrese un host al cual conectarse: "
            case "CONNECTED":
                self._prompt["prompt"] = MSG_PROMPT
        
        return self._prompt["prompt"]
    
    
    def _read_messages(self):
        while not self._stop_connection.is_set():
            try:
                data = self._client_socket.recv(BUFFER_SIZE)
            except Exception as e:
                self._handle_disconnect()
                return

            if data == b'':
                self._handle_disconnect()
                return

            parsedData = data.decode().split(":")
            user = parsedData[0]
            msg = ":".join(parsedData[1:])
            
            if data == '' or user == '' or msg == '':
                continue

            with patch_stdout():
                print(f"{user} ({self._host}) dice: {msg}")
    
    
    def _send_message(self, message):
        data = self._username + ":" + message
        self._client_socket.send(data.encode())
    

    def _handle_disconnect(self):
        if not self._stop_connection.is_set():
            with patch_stdout():
                print(f"SE PERDIÓ LA CONEXIÓN A '{self._host.upper()}'")
            self._set_state("DISCONNECTED")
            return


if __name__ == "__main__":
    app = App()
    app.start()
