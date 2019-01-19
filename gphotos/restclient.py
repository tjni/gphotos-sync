import six
from json import dumps
import logging
import requests

log = logging.getLogger(__name__)

'''
Defines very simple classes to create a callable interface to a REST api 
from a discovery REST description document.

Intended as a super simple replacement for google-api-python-client, using 
requests instead of httplib2

giles 2018
'''


class Method:
    def __init__(self, service, **k_args):
        self.path = None
        self.httpMethod = None
        self.service = service
        self.__dict__.update(k_args)
        self.path_args = []
        self.query_args = []
        if hasattr(self, 'parameters'):
            for key, value in six.iteritems(self.parameters):
                if value['location'] == 'path':
                    self.path_args.append(key)
                else:
                    self.query_args.append(key)

    def execute(self, body=None, **k_args):
        result = None
        path_args = {k: k_args[k] for k in self.path_args if k in k_args}
        query_args = {k: k_args[k] for k in self.query_args if k in k_args}
        path = self.service.base_url + self.make_path(path_args)
        if body:
            body = dumps(body)
        try:
            for retries in range(5):
                result = self.service.auth_session.request(self.httpMethod, data=body, url=path,
                                                           params=query_args)
                if result.status_code == requests.codes.ok:
                    break
            result.raise_for_status()
        except requests.exceptions.HTTPError:
            log.error('HTTP Error: %s\n on %s to %s with args:%s\n body:%s',
                      result.text, self.httpMethod, path, query_args, body)
            raise
        return result

    def make_path(self, path_args):
        result = self.path
        path_params = []
        for key, value in six.iteritems(path_args):
            path_param = '{{+{}}}'.format(key)
            if path_param in result:
                result = result.replace('{{+{}}}'.format(key), value)
                path_params.append(key)
        for key in path_params:
            path_args.pop(key)
        return result


class Collection:
    def __init__(self, name):
        self.collection_name = name


class RestClient:
    def __init__(self, api_url, auth_session):
        self.auth_session = auth_session
        service_document = self.auth_session.get(api_url).json()
        self.json = service_document
        self.base_url = str(service_document['baseUrl'])
        for c_name, collection in six.iteritems(service_document['resources']):
            new_collection = Collection(c_name)
            setattr(self, c_name, new_collection)
            for m_name, method in six.iteritems(collection['methods']):
                new_method = Method(self, **method)
                setattr(new_collection, m_name, new_method)