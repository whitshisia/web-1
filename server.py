import http.server
import os

class ServerException(Exception):
    '''For internal error reporting.'''
    pass

class RequestHandler(http.server.BaseHTTPRequestHandler):
    '''Handle HTTP requests by returning a fixed 'page'.'''
    '''if the requested path maps to a file, that file is served.
    if anything goes wrong, an error page is constructed.'''

    Cases = [
        'CaseNoFile',
        'CaseCGIFile',
        'CaseExistingFile',
        'CaseDirectoryIndexFile',
        'CaseDirectoryNoIndexFile',
        'CaseAlwaysFail'
    ]

    # Page to send back.
    Page = '''\
<html>
<body>
<table>
<tr> <td>Header</td>       <td>Value</td>      </tr>
<tr> <td>Date and time</td> <td>{date_time}</td>     </tr>
<tr> <td>Client host</td>   <td>{client_host}</td>     </tr>
<tr> <td>Client port</td>    <td>{client_port}</td>    </tr>
<tr> <td>Command </td>       <td>{command}</td>    </tr>
<tr> <td>Path</td>           <td>{path}</td>    </tr>
</table>
</body>
</html>
'''

    # Handle a GET request.
    def do_GET(self):
        # page = self.create_page()
        # self.send_page(page)
        try:
            # Figure out what exactly is being requested.
            self.full_path = os.getcwd() + self.path
            
            # Figure out how to handle it
            for case_name in self.Cases:
                case = globals()[case_name]()
                if case.test(self):
                    case.act(self)
                    break

        # Handle errors.
        except Exception as msg:
            self.handle_error(msg)

    def handle_file(self, full_path):
        try:
            with open(full_path, 'rb') as reader:
                content = reader.read()
            self.send_content(content)
        except IOError as msg:
            msg = "'{0}' cannot be read: {1}".format(self.path, msg)
            self.handle_error(msg) 

    Error_Page = '''\
<html>
<body>
<h1>Error accessing {path}</h1>
<p>{msg}</p>
</body>
</html>
'''

    def handle_error(self, msg):
        content = self.Error_Page.format(path=self.path, msg=msg)
        self.send_content(content.encode('utf-8'), 404) 
        
    # Send actual content
    def send_content(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)        

    def create_page(self): 
        values = {
            'date_time': self.date_time_string(),
            'client_host': self.client_address[0],
            'client_port' : self.client_address[1],
            'command': self.command,
            'path': self.path
        }
        page = self.Page.format(**values)
        return page

    def send_page(self, page):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page.encode('utf-8')) 
        
    # How to display a directory listing.
    Listing_Page = '''\
<html>
<body>
<ul>
{0}
</ul>
</body>
</html>
'''

    def list_dir(self, full_path):     
        try:
            entries = os.listdir(full_path)
            bullets = ['<li>{0}</li>'.format(e) for e in entries if not e.startswith('.')]
            page = self.Listing_Page.format('\n'.join(bullets))
            self.send_page(page)
        except OSError as msg:
            msg = "'{0}' cannot be listed: {1}".format(self.path, msg)
            self.handle_error(msg)

class CaseNoFile(object):
    '''File or directory does not exist.'''
    def test(self, handler):
        return not os.path.exists(handler.full_path)
    def act(self, handler):
        raise ServerException('{0} not found'.format(handler.path))

class CaseExistingFile(object):
    '''File exists.'''
    def test(self, handler):
        return os.path.isfile(handler.full_path)
    def act(self, handler):
        handler.handle_file(handler.full_path)

class CaseAlwaysFail(object):
    '''Base case if nothing else worked.'''  
    def test(self, handler):
        return True
    def act(self, handler):
        raise ServerException('Unknown object {0}'.format(handler.path))

class CaseDirectoryIndexFile(object):
    '''Serve index.html page for a directory.'''
    def index_path(self, handler):
        return os.path.join(handler.full_path, 'index.html')
    def test(self, handler):
        return os.path.isdir(handler.full_path) and os.path.isfile(self.index_path(handler))
    def act(self, handler):
        handler.handle_file(self.index_path(handler))

class CaseDirectoryNoIndexFile(object):
    '''Serve listing for a directory without an index.html page.'''
    def index_path(self, handler):
        return os.path.join(handler.full_path, 'index.html')
    def test(self, handler):
        return os.path.isdir(handler.full_path) and not os.path.isfile(self.index_path(handler))
    def act(self, handler):
        handler.list_dir(handler.full_path)

class CaseCGIFile(object):
    '''Something runnable.'''
    def test(self, handler):
        return os.path.isfile(handler.full_path) and handler.full_path.endswith('.py')
    def act(self, handler):
        handler.run_cgi(handler.full_path)

from datetime import datetime
print('''\
<html>
<body>
<p>Generated {0}</p>
</body>
</html>'''.format(datetime.now()))

#----------------------------------------------------------------------

if __name__ == '__main__':
    serverAddress = ('', 8080)
    server = http.server.HTTPServer(serverAddress, RequestHandler)
    print("Server started on port 8080")
    server.serve_forever()
