"""
A Python wrapper for Transmission's RPC interface.

>>> from transmission import Transmission
>>> client = Transmission()
>>> client('torrent-get', ids=range(1,11), fields=['name'])
{u'torrents': [
  {u'name': u'Elvis spotted in Florida.mov'},
  {u'name': u'Bigfoot sings the hits'},
  # ...
  {u'name': u'a-song-of-ice-and-fire_final-chapter.txt'}
]}
"""

__version__ = '0.4'

import json
import requests
from json_utils import (
    TransmissionJSONEncoder, TransmissionJSONDecoder)

CSRF_ERROR_CODE = 409
CSRF_HEADER = 'X-Transmission-Session-Id'

class BadRequest(Exception): pass

class Transmission(object):
    def __init__(self, host='localhost', port=9091, path='/transmission/rpc',
                 username=None, password=None, ssl=False):
        """
        Initialize the Transmission client.

        The default host, port and path are all set to Transmission's
        default.
        """
        self.url = "http://%s:%d%s" % (host, port, path)
        if ssl:
            self.url = "https://%s:%d%s" % (host, port, path)
        self.headers = {}
        self.tag = 0

        self.auth = None
        if username or password:
            self.auth = (username, password)

    def __call__(self, method, **kwargs):
        """
        Send request to Transmission's RPC interface.
        """
        response = self._make_request(method, **kwargs)
        return self._deserialize_response(response)

    def _make_request(self, method, **kwargs):
        body = json.dumps(self._format_request_body(method, **kwargs), cls=TransmissionJSONEncoder)
        response = requests.post(self.url, data=body, headers=self.headers, auth=self.auth, verify=False)
        if response.status_code == CSRF_ERROR_CODE:
            self.headers[CSRF_HEADER] = response.headers[CSRF_HEADER]
            return self._make_request(method, **kwargs)
        return response

    def _format_request_body(self, method, **kwargs):
        """
        Create a request object to be serialized and sent to Transmission.
        """
        fixed = {}
        # As Python can't accept dashes in kwargs keys, replace any
        # underscores with them here.
        for k, v in kwargs.iteritems():
            fixed[k.replace('_', '-')] = v
        return {"method": method, "tag": self.tag, "arguments": fixed}

    def _deserialize_response(self, response):
        """
        Return the response generated by the request object, raising
        BadRequest if there were any problems.
        """
        doc = json.loads(response.content, cls=TransmissionJSONDecoder)

        if doc['result'] != 'success':
            raise BadRequest("Request failed: '%s'" % doc['result'])

        if doc['tag'] != self.tag:
            raise BadRequest("Tag mismatch: (got %d, expected %d)" % (doc['tag'], self.tag))
        else:
            self.tag += 1

        if 'arguments' in doc:
            return doc['arguments'] or None
        return None
