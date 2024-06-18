import socket
import ssl
import os
import urllib.parse
import gzip

class URL:
    def __init__(self, url):
        if "://" not in url:
            raise ValueError("Invalid URL format. URL should include scheme (e.g., 'http://')")
        
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https", "file", "data", "view-source"], "Unsupported scheme"

        if self.scheme == "file":
            self.path = url
            self.host = None
            self.port = None
        elif self.scheme == "data":
            self.path = url
            self.host = None
            self.port = None
        elif self.scheme == "view-source":
            self.inner_url = URL(url)
        else:
            if "/" not in url:
                url += "/"
            self.host, self.path = url.split("/", 1)
            self.path = "/" + self.path
        
            if ":" in self.host:
                self.host, port = self.host.split(":", 1)
                self.port = int(port)
            else:
                if self.scheme == "https":
                    self.port = 443
                elif self.scheme == "http":
                    self.port = 80

    def request(self):
        if self.scheme == "file":
            return self.handle_file()
        elif self.scheme == "data":
            return self.handle_data()
        elif self.scheme == "view-source":
            return self.handle_view_source()
        else:
            return self.handle_http()

    def handle_file(self):
        try:
            with open(self.path, 'r') as f:
                return f.read()
        except IOError as e:
            raise ValueError(f"Error reading file: {e}")

    def handle_data(self):
        try:
            _, data = self.path.split(",", 1)
            return urllib.parse.unquote(data)
        except Exception as e:
            raise ValueError(f"Error handling data URL: {e}")

    def handle_view_source(self):
        body = self.inner_url.request()
        return body

    def handle_http(self):
        headers = {
            "Host": self.host,
            "Connection": "close",
            "User-Agent": "SimpleBrowser/1.0",
            "Accept-Encoding": "gzip"
        }
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))
        
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        
        header_str = "\r\n".join(f"{key}: {value}" for key, value in headers.items())
        request = f"GET {self.path} HTTP/1.1\r\n{header_str}\r\n\r\n"
        s.send(request.encode("utf-8"))
        
        response = s.makefile("rb", newline="\r\n")
        statusline = response.readline().decode("utf-8")
        version, status, explanation = statusline.split(" ", 2)
        
        response_headers = {}
        while True:
            line = response.readline().decode("utf-8")
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        
        if "content-encoding" in response_headers and response_headers["content-encoding"] == "gzip":
            content = gzip.decompress(response.read()).decode("utf-8")
        else:
            content = response.read().decode("utf-8")
        
        s.close()
        return content

def show(body):
    in_tag = False
    entity = ""
    in_entity = False
    for c in body:
        if in_entity:
            if c == ";":
                if entity == "lt":
                    print("<", end="")
                elif entity == "gt":
                    print(">", end="")
                else:
                    print(f"&{entity};", end="")
                entity = ""
                in_entity = False
            else:
                entity += c
        elif c == "&":
            in_entity = True
        elif c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")

def load(url):
    body = url.request()
    if url.scheme == "view-source":
        print(body)
    else:
        show(body)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        # Default file for quick testing if no URL is provided
        default_file = "/path/to/your/default/test/file.html"
        load(URL(f"file://{default_file}"))
    else:
        try:
            load(URL(sys.argv[1]))
        except ValueError as e:
            print(e)
