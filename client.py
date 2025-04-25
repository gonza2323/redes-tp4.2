from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
import threading
import socket
import time


PORT = 60000
BUFFER_SIZE = 1024
PROMPT = "> "


so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
so.bind(('0.0.0.0', PORT))

stop_event = threading.Event()


def get_username():
    username = None
    while True:
        username = input("Ingrese su nombre de usuario: ")
        if not username:
            print("El nombre de usuario no puede estar vacío")
        elif ":" in username:
            print("El nombre de usuario no puede contener dos puntos ':'")
        else:
            break
    return username


def read_messages():
    while not stop_event.is_set():
        data = so.recv(BUFFER_SIZE)
        parsedData = data.decode().split(":")
        user = parsedData[0]
        msg = ":".join(parsedData[1:])
        
        with patch_stdout():
            print(f"El usuario {user} ({so.getsockname()}) dice: {msg}")


def main():
    session = PromptSession()
    username = get_username()

    while True:
        try:
            host = input("Ingrese el host al cual conectarse: ")
            so.connect((host, PORT))
        except Exception as e:
            print(f"No se pudo conectar al host {host}:{PORT}")
            continue
        
        print(f"Conectado al host {host}:{PORT}")
        break
    
    reading_thread = threading.Thread(target=read_messages, daemon=True)
    reading_thread.start()

    while True:
        with patch_stdout():
            message = session.prompt(PROMPT)

            data = username + ":" + message
            so.send(data.encode())

            if message.lower() == "exit":
                stop_event.set()
                print("Saliendo...")
                time.sleep(0.5)
                break


if __name__ == "__main__":
    main()
