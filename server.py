from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from common import *
import threading
import socket
import time


PORT = 60000
BUFFER_SIZE = 1024
PROMPT = "> "

client_socket = None
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(('0.0.0.0', PORT))
server_socket.listen(1)

connection_event = threading.Event()
stop_event = threading.Event()


def stop_app():
    stop_event.set()
    server_socket.close()
    client_socket.close()
    print("Saliendo...")
    time.sleep(0.5)


def read_messages():
    while not stop_event.is_set():
        if connection_event.is_set():
            data = client_socket.recv(BUFFER_SIZE)

            if data == b'':
                if not stop_event.is_set():
                    stop_app()
                return

            parsedData = data.decode().split(":")
            user = parsedData[0]
            msg = ":".join(parsedData[1:])
            
            with patch_stdout():
                if msg.lower() == "exit":
                    print(f"El usuario {user} ({client_socket.getsockname()[0]}) terminó la conexión")
                    client_socket.close()
                    connection_event.clear()
                else:
                    print(f"El usuario {user} ({client_socket.getsockname()[0]}) dice: {msg}")
        else:
            time.sleep(0.1)


def await_connections():
    print("Esperando conexión del cliente...")
    global client_socket
    client_socket, _ = server_socket.accept()
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print(f"{client_socket.getsockname()[0]} se conectó al servidor")
    connection_event.set()


def main():
    session = PromptSession()
    username = get_username()

    server_thread = threading.Thread(target=await_connections, daemon=True)
    server_thread.start()

    reading_thread = threading.Thread(target=read_messages, daemon=True)
    reading_thread.start()

    while True:
        with patch_stdout():
            message = session.prompt(PROMPT)
            
            if connection_event.is_set():
                if message.lower() == "exit":
                    print("No se puede salir mientras esté conectado un cliente")
                else:
                    data = username + ":" + message
                    try:
                        print(f"Tú ({username}) ({client_socket.getsockname()[0]}) dices: {message}")
                        client_socket.send(data.encode())
                    except Exception as e:
                        print("Se perdió la conexión")
                        connection_event.clear()
                        server_thread.start()
            else:
                if message.lower() == "exit":
                    stop_app()
                    break
                else:
                    print("No está conectado un cliente, espere o utilice 'exit' para salir")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt as e:
        stop_app()
    except Exception as e:
        print(e)
    finally:
        server_socket.close()
        client_socket.close()