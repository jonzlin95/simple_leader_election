import etcd3
import time
import sys
from threading import Event, Thread
from http.server import BaseHTTPRequestHandler, HTTPServer


LEADER_KEY = '/leader'
LEASE_TTL = 10
SLEEP = 0.5
PORT = None
CLIENT = None
SERVER = None
THREAD = None

class MyHandler(BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
    def do_GET(s):
        """Respond to a GET request."""
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
        # s.wfile.write("<html><head><title>Title goes here.</title></head>")
        # s.wfile.write("<body><p>This is a test.</p>")
        # If someone went to "http://something.somewhere.net/foo/bar/",
        # then s.path equals "/foo/bar/".
        s.wfile.write("<html><head></head><h1>You accessed PORT: {}</h1></html>".format(PORT).encode())

def put_not_exist(lease):
    status, resps = CLIENT.transaction(
        compare=[
            CLIENT.transactions.version(LEADER_KEY) == 0
        ],
        success=[
            CLIENT.transactions.put(LEADER_KEY, PORT, lease)
        ],
        failure=[],
    )
    return status



def elect_leader():
    lease = CLIENT.lease(LEASE_TTL)
    print(lease)
    status = put_not_exist(lease)
    print(CLIENT.get(LEADER_KEY)[0].decode())
    print(PORT)
    return (CLIENT.get(LEADER_KEY)[0].decode() == PORT, lease)
    # return status, lease


if __name__ == "__main__":
    PORT = sys.argv[1]

    # Create your client
    CLIENT = etcd3.client(host="localhost", port=int(PORT))
    print(CLIENT)
    print(CLIENT.status())

    while True:
        print('trying election')
        is_leader, lease = elect_leader()

        if is_leader:
            print('leader')
            try:
                if not THREAD:
                    SERVER = HTTPServer(('', 8888), MyHandler)
                    THREAD = Thread(target = SERVER.serve_forever)
                    THREAD.daemon = True
                    THREAD.start()
                    print("We started the server?")
                    print(SERVER)
                    # This is annoying because you can't kill threads from outside in python, so this is just for example.

                while True:
                    # do work
                    lease.refresh()
                    print("We refreshed the lease")
                    time.sleep(SLEEP)
            except (Exception, KeyboardInterrupt):
                sys.exit()
            finally:
                lease.revoke()
        else:
            print('follower; standby')

            election_event = Event()
            def watch_cb(event):
                if isinstance(event, etcd3.events.DeleteEvent): # Watch for the key to be deleted.
                    election_event.set() # We set this event to trigger the while
            watch_id = CLIENT.add_watch_callback(LEADER_KEY, watch_cb)

            try:
                while not election_event.is_set():
                    print("Sleeping and waiting")
                    time.sleep(SLEEP)
                print('new election')
            except (Exception, KeyboardInterrupt):
                sys.exit()
            finally:
                CLIENT.cancel_watch(watch_id)