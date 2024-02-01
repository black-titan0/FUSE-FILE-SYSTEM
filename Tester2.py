import os
import threading


def list_files(directory):
    files = os.listdir(directory)
    return [file for file in files if os.path.isfile(os.path.join(directory, file))]


def write_id_to_file(file_path, thread_id, repetitions):
    with open(file_path, 'a') as file:
        for _ in range(repetitions):
            file.write(f'ThreadID: {thread_id}\n')


def thread_function(thread_id, directory, file_path, repetitions):
    print(f"Thread {thread_id} executing 'ls' on {directory}")
    files = list_files(directory)

    if not files:
        print(f"No files in the directory {directory} for Thread {thread_id}")
        return

    print(f"Thread {thread_id} writing its ID to the file {file_path} {repetitions} times")
    write_id_to_file(file_path, thread_id, repetitions)


if __name__ == '__main__':
    # Set the number of threads (X), the directory path (Y), file path, and repetitions
    num_threads = 5
    directory_path = './mp'
    file_path = './mp/safa'
    repetitions = 100000

    # Create and start threads
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=thread_function, args=(i + 1, directory_path, file_path, repetitions))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print("All threads have completed.")
