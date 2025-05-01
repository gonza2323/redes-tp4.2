from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
import threading
import socket
import time


PORT = 60000
BUFFER_SIZE = 1024
PROMPT = "> "


class App:
    _username = None
    _app_state = None
    _server_socket = None
    _client_socket = None
    _client_ip = None
    _stop_app = None
    _stop_connection = None
    _session = None
    _read_messages_thread = None
    _server_thread = None


    def __init__(self):
        self._stop_connection = threading.Event()
        self._stop_app = threading.Event()
        self._session = PromptSession()
    

    def start(self):
        try:
            self._username = self._get_username()
            self._set_state("DISCONNECTED")
            
            while not self._stop_app.is_set():
                self._handle_user_input()

        except KeyboardInterrupt:
            self.stop()
        finally:
            self._stop_connection.set()
            self._stop_app.set()
            if self._client_socket:
                self._client_socket.shutdown(socket.SHUT_WR)
                self._client_socket.close()
                self._client_socket = None
        

    def stop(self):
        self._stop_connection.set()
        self._stop_app.set()
        if self._client_socket:
            self._client_socket.shutdown(socket.SHUT_WR)
            self._client_socket.close()
            self._client_socket = None
        if self._server_socket:
            self._server_socket.shutdown(socket.SHUT_WR)
            self._server_socket.close()
            self._server_socket = None
        print("Saliendo...")
        time.sleep(0.2)


    def _handle_user_input(self):
        user_input = self._session.prompt(PROMPT)

        match self._app_state:
            case "DISCONNECTED":
                if (user_input.lower() == 'exit'):
                    self.stop()
                    return
                
                with patch_stdout():
                    print("No está conectado un cliente, espere o utilice 'exit' para salir")
                                        
            case "CONNECTED":
                if (user_input.lower() == 'exit'):
                    with patch_stdout():
                        print("No se puede salir mientras esté conectado un cliente")
                    return

                if (user_input.strip() != ''):
                    self._send_message(user_input)


    def _set_state(self, new_state):
        self._app_state = new_state
        
        match new_state:
            case "DISCONNECTED":
                self._stop_connection.set()
                self._client_ip = None
                if self._client_socket:
                    self._client_socket.shutdown(socket.SHUT_WR)
                    self._client_socket.close()
                    self._client_socket = None
                
                self._server_thread = threading.Thread(target=self._wait_for_connections, daemon=True)
                self._server_thread.start()

            case "CONNECTED":
                self._stop_connection.clear()
                self._read_messages_thread = threading.Thread(target=self._read_messages, daemon=True)
                self._read_messages_thread.start()

    
    def _wait_for_connections(self):
        with patch_stdout():
            print("Esperando conexión del cliente...")

        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind(('0.0.0.0', PORT))
            self._server_socket.listen(1)

            self._client_socket, (self._client_ip, _) = self._server_socket.accept()
            self._client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            if self._server_socket:
                self._server_socket.shutdown(socket.SHUT_WR)
                self._server_socket.close()
                self._server_socket = None
        except Exception as e:
            print(e)
        
        with patch_stdout():
            print(f"{self._client_ip} se conectó al servidor")
        
        self._set_state("CONNECTED")
    
    
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
                print(f"{user} ({self._client_ip}) dice: {msg}")
    
    
    def _send_message(self, message):
        data = self._username + ":" + message
        self._client_socket.send(data.encode())
    

    def _handle_disconnect(self):
        if not self._stop_connection.is_set():
            with patch_stdout():
                print(f"SE PERDIÓ LA CONEXIÓN A '{self._client_ip.upper()}'")
            self._set_state("DISCONNECTED")
            return


    def _get_username(self):
        username = None
        while True:
            username = self._session.prompt("Ingrese su nombre de usuario: ")
            if not username:
                print("El nombre de usuario no puede estar vacío")
            elif ":" in username:
                print("El nombre de usuario no puede contener dos puntos ':'")
            else:
                break
        return username


if __name__ == "__main__":
    app = App()
    app.start()
