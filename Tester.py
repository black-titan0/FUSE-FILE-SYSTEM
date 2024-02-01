import os
import threading
import random

def list_files(directory):
    files = os.listdir(directory)
    return [file for file in files if os.path.isfile(os.path.join(directory, file))]

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def append_thread_id(file_path, thread_id):
    with open(file_path, 'a') as file:
        file.write(f'ThreadID: {thread_id}\n')

def thread_function(thread_id, directory):
    print(f"Thread {thread_id} executing 'ls' on {directory}")
    files = list_files(directory)
    
    if not files:
        print(f"No files in the directory {directory} for Thread {thread_id}")
        return
    
    selected_file = random.choice(files)
    file_path = os.path.join(directory, selected_file)
    
    print(f"Thread {thread_id} selected file: {selected_file}")
    
    if random.choice([False, False]):
        file_content = read_file(file_path)
        print(f"Thread {thread_id} read file content: {file_content}")
    else:
        append_thread_id(file_path, thread_id)
        print(f"Thread {thread_id} appended its ID to the file {selected_file}")

# Set the number of threads (X) and the directory path (Y)

if __name__ == '__main__':

    num_threads = 10000
    directory_path = './mp'

    # Create and start threads
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=thread_function, args=(i+1, directory_path))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print("All threads have completed.")
