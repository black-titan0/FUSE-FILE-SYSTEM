import os
import threading
import random

def list_files(directory):
    files = os.listdir(directory)
    return [file for file in files if os.path.isfile(os.path.join(directory, file))]

def write_huge_string_to_file(file_path, thread_id, repetitions):
    huge_string = f'ThreadID: {thread_id}\n' * repetitions
    with open(file_path, 'a') as file:
        file.write(huge_string)

def thread_function(thread_id, directory, repetitions):
    print(f"Thread {thread_id} executing 'ls' on {directory}")
    files = list_files(directory)
    
    if not files:
        print(f"No files in the directory {directory} for Thread {thread_id}")
        return
    
    selected_file = random.choice(files)
    file_path = os.path.join(directory, selected_file)
    
    print(f"Thread {thread_id} selected file: {selected_file}")
    print(f"Thread {thread_id} trying to write a huge string to the file {file_path}")
    
    try:
        write_huge_string_to_file(file_path, thread_id, repetitions)
        print(f"Thread {thread_id} successfully wrote to the file {file_path}")
    except Exception as e:
        print(f"Thread {thread_id} encountered an error: {e}")

# Set the number of threads (X), the directory path (Y), and repetitions
num_threads = 1
directory_path = './mp'
repetitions = 100000000

# Create and start threads
threads = []
for i in range(num_threads):
    thread = threading.Thread(target=thread_function, args=(i+1, directory_path, repetitions))
    threads.append(thread)
    thread.start()

# Wait for all threads to complete
for thread in threads:
    thread.join()

print("All threads have completed.")