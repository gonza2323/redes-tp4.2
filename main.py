from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
import threading
import socket
import time


PORT = 60000
BUFFER_SIZE = 1024
PROMPT = "> "


so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
so.bind(('0.0.0.0', PORT))
so.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

stop_event = threading.Event()


def get_username():
    username = input("Ingrese su nombre de usuario: ")
    return username


def read_messages():
    while not stop_event.is_set():
        (data, (address, _)) = so.recvfrom(BUFFER_SIZE)
        parsedData = data.decode().split(":")
        user = parsedData[0]
        msg = ":".join(parsedData[1:])
        
        with patch_stdout():
            template = f"El usuario {user} ({address}) "
            if msg == "nuevo":
                print(template + "se ha unido a la conversación")
            elif msg == "exit":
                print(template + "ha abandonado la conversación")
            else:
                print(template + f"dice: {msg}")


def main():
    session = PromptSession()
    username = get_username()
    reading_thread = threading.Thread(target=read_messages)
    reading_thread.start()

    join_msg = username + ":nuevo"
    so.sendto(join_msg.encode(), ('255.255.255.255', PORT))

    while True:
        with patch_stdout():
            user_input = session.prompt(PROMPT)
            print('\r', end="")

            msg = username + ":" + user_input
            so.sendto(msg.encode(), ('255.255.255.255', PORT))
            
            if user_input.lower() == "exit":
                stop_event.set()
                reading_thread.join()
                print("Saliendo...")
                time.sleep(1)
                break


if __name__ == "__main__":
    main()
