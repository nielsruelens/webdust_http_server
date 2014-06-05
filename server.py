import time, json, erppeek
import BaseHTTPServer
from urlparse import urlparse, parse_qs



config = False


##############################################################################
#
#    Handler class for the server. It will handle all incoming requests.
#
##############################################################################
class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    partner = False
    server_response_type = 'application/json'

    def authenticate(self, headers):
        ''' MyHandler:authenticate()
            ------------------------
            This method reads the headers and makes
            sure it is valid and authorized.
            --------------------------------------- '''

        # Make sure a token is provided
        # -----------------------------
        if "x-token" not in headers:
            log('Invalid request sent to server: no identification provided.')
            self.send_response(400)
            self.send_header("Content-type", self.server_response_type)
            self.end_headers()
            self.wfile.write(json.dumps({'result':'You did not provide any authentication.'}))
            return False

        # Make sure the token is known by the server
        # ------------------------------------------
        self.partner = [x for x in config['partners'] if x['token'] == headers['x-token'] ]
        if not self.partner:
            log('Invalid request sent to server: unknown login credentials: {!s}'.format(headers['x-token']))
            self.send_response(401)
            self.send_header("Content-type", self.server_response_type)
            self.end_headers()
            self.wfile.write(json.dumps({'result':'Not authorized.'}))
            return False
        self.partner = self.partner[0]


        # Make sure the data type is accepted
        # -----------------------------------
        if "content-type" not in headers:
            log('Invalid request sent to server: no content-type provided.')
            self.send_response(400)
            self.send_header("Content-type", self.server_response_type)
            self.end_headers()
            self.wfile.write(json.dumps({'result':'You did not provide the content-type.'}))
            return False
        if headers['content-type'] != 'application/json' and headers['content-type'] != 'application/xml':
            log('Invalid request sent to server: incompatible content-type provided.')
            self.send_response(400)
            self.send_header("Content-type", self.server_response_type)
            self.end_headers()
            self.wfile.write(json.dumps({'result':'You did not provide a valid content-type.'}))
            return False

        return True




    def do_POST(self):
        ''' MyHandler:do_POST()
            -------------------
            This method handles all POST requests sent to the server.
            --------------------------------------------------------- '''

        # Authenticate this request
        # -------------------------
        if not self.authenticate(self.headers.dict):
            return

        # Determine basic action type
        # (EDI is the only thing supported at the moment)
        # -----------------------------------------------
        if self.path[:5] != '/edi/':
            log('Invalid request sent to server: unknown path provided: {!s}'.format(self.path))
            self.send_response(404)
            self.send_header("Content-type", self.server_response_type)
            self.end_headers()
            self.wfile.write(json.dumps({'result':'Unknown path.'}))
            return False

        self.handle_edi_request()
        return True


    def handle_edi_request(self):
        ''' MyHandler:handle_edi_request()
            ------------------------------
            This method handles all EDI requests sent to the server.
            -------------------------------------------------------- '''

        # Validate the routing
        # --------------------
        split_path = self.path.split('?')
        flow = [x for x in config['edi_routing'] if x['path'] == split_path[0] ]
        if not flow:
            log('Invalid request sent to server: unknown path provided: {!s}'.format(self.path))
            self.send_response(404)
            self.send_header("Content-type", self.server_response_type)
            self.end_headers()
            self.wfile.write(json.dumps({'result':'Unknown path.'}))
            return False
        flow = flow[0]

        # Validate all required information is present
        # --------------------------------------------
        parameters = parse_qs(urlparse(self.path).query)
        if not parameters:
            log('Invalid request sent to server: missing GET parameter reference.')
            self.send_response(400)
            self.send_header("Content-type", self.server_response_type)
            self.end_headers()
            self.wfile.write(json.dumps({'result':'Bad request. Missing parameter reference'}))
            return False

        length = int(self.headers.getheader('content-length'))
        try:
            content = self.rfile.read(length)
        except Exception as e:
            log('Invalid request sent to server: request data is broken. Error given: {!s}'.format(str(e)))
            self.send_response(400)
            self.send_header("Content-type", self.server_response_type)
            self.end_headers()
            self.wfile.write(json.dumps({'result':'Bad request.'}))
            return False

        data_type = 'json'
        if self.headers.dict['content-type'] != 'application/json':
            data_type = 'xml'

        # Connect to OpenERP
        # ------------------
        try:
            client = erppeek.Client('http://{!s}:{!s}'.format(config['openerp']['host'],config['openerp']['port']),
                                    config['openerp']['database'],
                                    config['openerp']['user'],
                                    config['openerp']['password'])
        except Exception:
            log('OpenERP target server cannot be reached.')
            self.send_response(503)
            self.send_header("Content-type", self.server_response_type)
            self.end_headers()
            self.wfile.write(json.dumps({'result':'Internal server error: target server cannot be reached. Contact the handig.nl system admins please.'}))
            return False


        model = client.model('clubit.tools.edi.document.incoming')
        result = model.create_from_web_request(self.partner['id'], flow['flow'], parameters['reference'][0], content, data_type)
        if result == True:
            log('OpenERP target server has accepted the request.')
            self.send_response(200)
            self.send_header("Content-type", self.server_response_type)
            self.end_headers()
            self.wfile.write(json.dumps({'result':'Your data has been successfully received by our target system.'}))
        else:
            log('OpenERP target has rejected the request.')
            self.send_response(503)
            self.send_header("Content-type", self.server_response_type)
            self.end_headers()
            self.wfile.write(json.dumps({'result':result}))










##############################################################################
#
#    Main program that starts the server
#
##############################################################################

def log(message):
    print time.asctime(), message



if __name__ == '__main__':

    log("Starting the Webdust EDI recipient server.")

    # Read the customizing from config.json
    # -------------------------------------
    log("Reading the required customizing from config.json.")
    try:
        with open("config.json") as f:
            config = f.read()
        log("Customizing has been found.")
    except Exception as e:
        log("Couldn't find config.json file. Please install the server first.")
        log("Server has not been started.")
        exit()

    try:
        config = json.loads(config)
    except Exception as e:
        log("The config.json file did not contain valid JSON. Error given is: {!s}".format(str(e)))
        log("Please re-install the server or adjust the configuration.")
        log("Server has not been started.")
        exit()
    log("Customizing was found and successfully loaded.")



    # Instantiate the server
    # ----------------------
    log("Instantiating the server.")
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class((config['server']['host'], config['server']['port']), MyHandler)

    # Start the server
    # ----------------
    log("Starting the server at {!s}:{!s}".format(config['server']['host'], config['server']['port']))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    log("Stopping the server at {!s}:{!s}".format(config['server']['host'], config['server']['port']))




































