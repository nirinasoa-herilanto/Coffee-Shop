import os
import json
from flask import request, _request_ctx_stack, abort
from functools import wraps
from jose import jwt
from urllib.request import urlopen
from dotenv import load_dotenv

load_dotenv()

AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
ALGORITHMS = ['RS256']
API_AUDIENCE = os.getenv('API_AUDIENCE')

## AuthError Exception
'''
AuthError Exception
A standardized way to communicate auth failure modes
'''
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


## Auth Header

def get_token_auth_header():
    if 'Authorization' not in request.headers:
        raise AuthError({
            "code": "no permissions",
            "description": "unauthorized, permissions is required"
        }, 401)
    
    auth_headers = request.headers.get('Authorization', None)
    
    if auth_headers is None:
        raise AuthError({
            "code": "no authorization",
            "description": "unthorized, authorization is required"
        }, 401)
    
    auth_token = auth_headers.split(' ')
    
    if len(auth_token) != 2:
        raise AuthError({
            "code": "invalid format",
            "description": "unthorized, invalid token"
        }, 401)
    
    if auth_token[0].lower() != "bearer":
        raise AuthError({
            "code": "invalid porter",
            "description": "unthorized, wrong or invalid porter token"
        }, 401)
        
    return auth_token[1]


def check_permissions(permission, payload):
    if 'permissions' not in payload:
        raise AuthError({
            "code": "invalid claims",
            "description": "permissions are not included in JWT"
        }, 400)
    
    if permission not in payload.get('permissions'):
        raise AuthError({
            "code": "unthorized",
            "description": "permission not found"
        }, 403)
    
    return True

def verify_decode_jwt(token):
    jsonurl = urlopen(f'https://{AUTH0_DOMAIN}/.well-known/jwks.json')
    jwks = json.loads(jsonurl.read())
    
    unverified_header = jwt.get_unverified_header(token)
    
    rsa_key = {}
    if 'kid' not in unverified_header:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization malformed.'
        }, 401)

    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }
    
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer='https://' + AUTH0_DOMAIN + '/'
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise AuthError({
                'code': 'token_expired',
                'description': 'Token expired.'
            }, 401)

        except jwt.JWTClaimsError:
            raise AuthError({
                'code': 'invalid_claims',
                'description': 'Incorrect claims. Please, check the audience and issuer.'
            }, 401)
        except Exception:
            raise AuthError({
                'code': 'invalid_header',
                'description': 'Unable to parse authentication token.'
            }, 400)
    raise AuthError({
                'code': 'invalid_header',
                'description': 'Unable to find the appropriate key.'
            }, 400)


def requires_auth(permission=''):
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            payload = verify_decode_jwt(token)
            
            check_permissions(permission, payload)
                
            return f(payload, *args, **kwargs)

        return wrapper
    
    return requires_auth_decorator