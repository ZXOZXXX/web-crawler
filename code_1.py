import os
import threading
from queue import Queue
from urllib.parse import urlparse, urljoin
from urllib.request import urlopen
from html.parser import HTMLParser
from datetime import datetime
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, scrolledtext

# Helper functions for URL and domain processing
def get_domain_name(url):
    try:
        return '.'.join(urlparse(url).netloc.split('.')[-2:])
    except Exception as e:
        print(f"Error in get_domain_name: {e}")
        return ''

# Helper functions for file operations
def create_project_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def create_data_files(project_name, base_url):
    queue = os.path.join(project_name, 'queue.txt')
    crawled = os.path.join(project_name, 'crawled.txt')

    if not os.path.isfile(queue):
        write_file(queue, f'URL,Status Code,Date Crawled\n{base_url},Pending,{datetime.now().isoformat()}')
    if not os.path.isfile(crawled):
        write_file(crawled, 'URL,Status Code,Date Crawled\n')

def write_file(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(data)

def add_data_to_file(path, data):
    with open(path, 'a', encoding='utf-8') as file:
        file.write(data + '\n')

def delete_file_content(path):
    with open(path, 'w'):
        pass

def file_to_set(fileName):
    results = set()
    with open(fileName, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                results.add(line.split(',')[0])
    return results

def set_to_file(fileName, setName, status=''):
    delete_file_content(fileName)
    with open(fileName, 'a', encoding='utf-8') as f:
        f.write('URL,Status Code,Date Crawled\n')
        for link in sorted(setName):
            f.write(f'{link},{status},{datetime.now().isoformat()}\n')

# HTML parsing and link extraction
class LinkFinder(HTMLParser):
    def __init__(self, base_url, page_url):
        super().__init__()
        self.base_url = base_url
        self.page_url = page_url
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for (attribute, value) in attrs:
                if attribute == 'href':
                    url = urljoin(self.base_url, value)
                    self.links.add(url)

    def page_links(self):
        return self.links

# Spider class for crawling web pages
class Spider:
    project_name = ''
    base_url = ''
    domain_name = ''
    queue_file = ''
    crawled_file = ''
    queue = set()
    crawled = set()

    def __init__(self, project_name, base_url, domain_name):
        Spider.project_name = project_name
        Spider.base_url = base_url
        Spider.domain_name = domain_name
        Spider.queue_file = os.path.join(Spider.project_name, "queue.txt")
        Spider.crawled_file = os.path.join(Spider.project_name, "crawled.txt")
        self.boot()
        self.crawl_page('First spider', Spider.base_url)

    @staticmethod
    def boot():
        create_project_dir(Spider.project_name)
        create_data_files(Spider.project_name, Spider.base_url)
        Spider.queue = file_to_set(Spider.queue_file)
        Spider.crawled = file_to_set(Spider.crawled_file)

    @staticmethod
    def crawl_page(spiderName, pageUrl):
        if pageUrl not in Spider.crawled:
            print(f'{spiderName} now crawling: {pageUrl}')
            links = Spider.gather_links(pageUrl)
            status_code = Spider.get_status_code(pageUrl)
            Spider.add_links_to_queue(links)
            Spider.queue.remove(pageUrl)
            Spider.crawled.add(pageUrl)
            Spider.update_files(status_code)

    @staticmethod
    def gather_links(pageUrl):
        html_string = ''
        try:
            response = urlopen(pageUrl)
            if 'text/html' in response.getheader('Content-Type'):
                html_bytes = response.read()
                html_string = html_bytes.decode('utf-8')
            finder = LinkFinder(Spider.base_url, pageUrl)
            finder.feed(html_string)
        except Exception as e:
            print(f'Error in gather_links: {e}')
            return set()

        return finder.page_links()

    @staticmethod
    def get_status_code(url):
        try:
            response = urlopen(url)
            return response.getcode()
        except Exception as e:
            print(f'Error in get_status_code: {e}')
            return 'Error'

    @staticmethod
    def add_links_to_queue(links):
        for url in links:
            if url in Spider.queue or url in Spider.crawled or Spider.domain_name not in url:
                continue
            Spider.queue.add(url)

    @staticmethod
    def update_files(status_code):
        set_to_file(Spider.queue_file, Spider.queue, 'Pending')
        set_to_file(Spider.crawled_file, Spider.crawled, status_code)

# Threading for concurrent crawling
NUMBER_OF_THREADS = 8
stop_threads = False

def start_crawling(url, progress_text):
    global stop_threads
    PROJECT_NAME = get_domain_name(url)
    DOMAIN_NAME = get_domain_name(url)
    QUEUE_FILE = os.path.join(PROJECT_NAME, 'queue.txt')
    CRAWLED_FILE = os.path.join(PROJECT_NAME, 'crawled.txt')

    queue = Queue()
    Spider(PROJECT_NAME, url, DOMAIN_NAME)

    def create_threads():
        for _ in range(NUMBER_OF_THREADS):
            t = threading.Thread(target=work)
            t.daemon = True
            t.start()

    def work():
        while not stop_threads:
            url = queue.get()
            if url is None:
                queue.task_done()
                break
            Spider.crawl_page(threading.current_thread().name, url)
            queue.task_done()
            update_progress()

    def create_jobs():
        for link in file_to_set(QUEUE_FILE):
            queue.put(link)
        queue.join()
        crawl()

    def crawl():
        queue_links = file_to_set(QUEUE_FILE)
        if queue_links:
            update_progress(f"Links Left: {len(queue_links)}")
            create_jobs()
        else:
            update_progress("Crawling finished.")

    def update_progress(message="Crawling in progress..."):
        progress_text.configure(state=tk.NORMAL)
        progress_text.insert(tk.END, message + '\n')
        progress_text.configure(state=tk.DISABLED)
        progress_text.yview(tk.END)

    def stop_crawling():
        global stop_threads
        stop_threads = True
        update_progress("Crawling stopped.")

    # Start a timer to stop crawling after a fixed duration (e.g., 5 minutes)
    def stop_after_duration(duration=300):
        global stop_threads
        threading.Timer(duration, stop_crawling).start()

    create_threads()
    stop_after_duration()

    try:
        crawl()
    except Exception as e:
        print(f"Error during crawling: {e}")

def show_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return content
    except Exception as e:
        return f"Error reading file: {e}"

def on_queue_show():
    PROJECT_NAME = get_domain_name(url_entry.get())
    QUEUE_FILE = os.path.join(PROJECT_NAME, 'queue.txt')
    content = show_file_content(QUEUE_FILE)
    show_file_content_popup("Queue File", content)

def on_crawled_show():
    PROJECT_NAME = get_domain_name(url_entry.get())
    CRAWLED_FILE = os.path.join(PROJECT_NAME, 'crawled.txt')
    content = show_file_content(CRAWLED_FILE)
    show_file_content_popup("Crawled File", content)

def show_file_content_popup(title, content):
    popup = tk.Toplevel()
    popup.title(title)
    popup.geometry("700x600")  # Set the dimensions of the popup window

    text = scrolledtext.ScrolledText(popup, wrap=tk.WORD, state=tk.NORMAL, font=("Helvetica", 15))
    text.insert(tk.END, content)
    text.configure(state=tk.DISABLED)
    text.pack(expand=True, fill=tk.BOTH)

def run_gui():
    def on_start():
        url = url_entry.get()
        if url:
            start_button.configure(state=tk.DISABLED)  # Disable the start button
            threading.Thread(target=start_crawling, args=(url, progress_text), daemon=True).start()
        else:
            messagebox.showerror("Input Error", "Please enter a valid URL.")

    # GUI setup
    app = ctk.CTk()  # Use customtkinter's main window
    app.geometry("700x600")
    ctk.set_appearance_mode("dark")  # Call set_appearance_mode from the module
    app.title("Web Crawler")

    frame = ctk.CTkFrame(app, fg_color='black')
    frame.pack(padx=10, pady=10, fill='both', expand=True)

    # Label with increased font size
    tk.Label(frame, text="Enter URL to Crawl:", fg='white', bg='black', font=('Helvetica', 16, 'bold')).pack(pady=5)
    
    global url_entry
    url_entry = ctk.CTkEntry(frame, width=400, fg_color='gray20', text_color='white', border_width=2)
    url_entry.pack(pady=5)

    # Start button with rounded corners and yellow border effect
    global start_button
    start_button = ctk.CTkButton(frame, text="Start Crawling", command=on_start, 
                                fg_color='black', hover_color='#555555', 
                                corner_radius=20, text_color='white', font=('Helvetica', 14, 'bold'))
    start_button.pack(pady=5)
    
    # Apply a yellow border effect manually
    start_button.configure(border_color='#FFD700', border_width=2)

    # Queue show button
    queue_button = ctk.CTkButton(frame, text="Show Queue File", command=on_queue_show, 
                                fg_color='black', hover_color='#555555', 
                                corner_radius=20, text_color='white', font=('Helvetica', 14, 'bold'))
    queue_button.pack(pady=5)
    
    # Apply a yellow border effect manually
    queue_button.configure(border_color='#FFD700', border_width=2)

    # Crawled show button
    crawled_button = ctk.CTkButton(frame, text="Show Crawled File", command=on_crawled_show, 
                                  fg_color='black', hover_color='#555555', 
                                  corner_radius=20, text_color='white', font=('Helvetica', 14, 'bold'))
    crawled_button.pack(pady=5)
    
    # Apply a yellow border effect manually
    crawled_button.configure(border_color='#FFD700', border_width=2)

    progress_text = ctk.CTkTextbox(frame, width=80, height=20, 
                                   fg_color='gray20', text_color='white', state=tk.DISABLED)
    progress_text.pack(pady=10, fill='both', expand=True)

    app.mainloop()

if __name__ == "__main__":
    run_gui()
