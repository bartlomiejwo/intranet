import json

import requests


class ApiIntegrationService:
    CONNECT_TIMEOUT_COUNTER = 'connect_timeout_counter'
    READ_TIMEOUT_COUNTER = 'read_timeout_counter'
    CONNECTION_ERROR_COUNTER = 'connection_error_counter'

    PARTIAL_CONTENT_STATUS_CODE = 206
    
    def __init__(self, root_url, encoding, timeout, max_connect_timeout=3, max_read_timeout=3, max_connection_error=3):
        self.root_url = root_url

        self.encoding = encoding
        self.timeout = timeout
        self.max_connect_timeout = max_connect_timeout
        self.connect_timeout_counter = 0
        self.max_read_timeout = max_read_timeout
        self.read_timeout_counter = 0
        self.max_connection_error = max_connection_error
        self.connection_error_counter = 0

    def get_response(self, url, headers, params={}):
        return self.response(requests.get, url, headers=headers, params=params, timeout=self.timeout)

    def post_response(self, url, headers, data, params={}):
        return self.response(requests.post, url, headers=headers, json=data, params=params, timeout=self.timeout)

    def get_response_data(self, url, headers, params={}):
        response = self.get_response(url, headers, params)
        response_data = json.loads(response.text)

        if response.status_code == ApiIntegrationService.PARTIAL_CONTENT_STATUS_CODE:
            self.handle_partial_content_response_data(response.headers, url, headers, params, response_data)

        return response_data

    def post_response_data(self, url, headers, data, params={}):
        response = self.post_response(url, headers, data, params)
        response_data = json.loads(response.text)

        if response.status_code == ApiIntegrationService.PARTIAL_CONTENT_STATUS_CODE:
            self.handle_partial_content_response_data(response.headers, url, headers, params, response_data)

        return response_data
    
    def handle_partial_content_response_data(self, response_headers, url, request_headers, params, response_data):
        try:
            accept_range = response_headers['Accept-Range']
            content_range = response_headers['Content-Range']
        except KeyError as e:
            raise ResponseHeaderRangeKeyError(str(e))
        else:
            try:
                max_number_of_items = int(accept_range.split(' ')[-1])
                range_data = content_range.split('-')[-1].split('/')
                range_end = int(range_data[0])
                range_limit = int(range_data[1])
            except IndexError as e:
                raise ResponseHeaderRangeIndexError(str(e))
            except ValueError as e:
                raise ResponseHeaderRangeValueError(str(e))
            else:
                while range_end < range_limit:
                    next_range = f'{range_end+1}-{range_end+max_number_of_items}'
                    range_end += max_number_of_items

                    params = [x for x in params if x[0] != 'range']
                    params += (('range', next_range), )

                    response = self.get_response(url, request_headers, params)
                    response_data.extend(json.loads(response.text))

    def response(self, method, *args, **kwargs):
        while True:
            try:
                response = method(*args, **kwargs)
                response.encoding = self.encoding

                self.reset_error_counters(
                    ApiIntegrationService.CONNECT_TIMEOUT_COUNTER, 
                    ApiIntegrationService.READ_TIMEOUT_COUNTER, 
                    ApiIntegrationService.CONNECTION_ERROR_COUNTER
                )

                if response:
                    return response

                raise ResponseError(f'\n{response.status_code}\n\n{response.headers}\n\n{response.text}')
            except requests.exceptions.ConnectTimeout:
                self.handle_connect_timeout()
            except requests.ReadTimeout:
                self.handle_read_timeout()
            except requests.ConnectionError:
                self.handle_connection_error()
            except requests.exceptions.RequestException as e:
                raise RequestsException(f'Undefined requests error: {str(e)}')

    def handle_connect_timeout(self):
        self.connect_timeout_counter += 1

        if self.connect_timeout_counter >= self.max_connect_timeout:
            self.reset_error_counters(ApiIntegrationService.CONNECT_TIMEOUT_COUNTER)
            raise ConnectTimeout()

    def handle_read_timeout(self):
        self.read_timeout_counter += 1

        if self.read_timeout_counter >= self.max_read_timeout:
            self.reset_error_counters(ApiIntegrationService.READ_TIMEOUT_COUNTER)
            raise ReadTimeout()

    def handle_connection_error(self):
        self.connection_error_counter += 1

        if self.connection_error_counter >= self.max_connection_error:
            self.reset_error_counters(ApiIntegrationService.CONNECTION_ERROR_COUNTER)
            raise ConnectionErrorOccurred()

    def reset_error_counters(self, *args):
        for counter_name in args:
            try:
                self.__getattribute__(counter_name)
            except AttributeError as exception:
                raise exception
            else:
                self.__setattr__(counter_name, 0)

    def print_response_info(self, response, title):
        print('----------------------------------')
        print(title)
        print('----------------------------------')
        print(response)
        print(response.headers)
        print(response.text)

        if response.text:
            json_response = json.loads(response.text)
            
            for item in json_response:
                print(item, '\n')

        print('----------------------------------')


class RequestsException(Exception):
    pass


class ResponseError(Exception):
    pass


class ResponseHeaderRangeKeyError(Exception):
    pass


class ResponseHeaderRangeIndexError(Exception):
    pass


class ResponseHeaderRangeValueError(Exception):
    pass


class ConnectTimeout(RequestsException):
    pass


class ReadTimeout(RequestsException):
    pass


class ConnectionErrorOccurred(RequestsException):
    pass
