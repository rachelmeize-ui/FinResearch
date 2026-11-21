"""Explicit remote configuration; default remains loopback-only."""
import base64
import binascii
import hmac
import os
from urllib.parse import urlsplit


def origin():
    return (os.environ.get('FINRESEARCH_PUBLIC_ORIGIN') or os.environ.get('RENDER_EXTERNAL_URL', '')).rstrip('/')


def validate(bind):
    if bind in ('127.0.0.1', 'localhost', '::1'):
        return
    public = urlsplit(origin())
    if public.scheme != 'https' or not public.hostname or public.path or public.query or public.fragment or public.username:
        raise ValueError('远程运行需要配置完整的 HTTPS 网站地址 FINRESEARCH_PUBLIC_ORIGIN。')
    if len(os.environ.get('FINRESEARCH_ACCESS_PASSWORD', '')) < 24:
        raise ValueError('远程运行需要至少24位的独立访问密码 FINRESEARCH_ACCESS_PASSWORD。')


def host_allowed(host, port):
    return host in (f'127.0.0.1:{port}', f'localhost:{port}') or bool(origin() and host == urlsplit(origin()).netloc)


def authorized(header):
    password = os.environ.get('FINRESEARCH_ACCESS_PASSWORD', '')
    if not password:
        return True  # Remote startup without a password is refused by validate().
    try:
        scheme, encoded = header.split(' ', 1)
        if scheme.lower() != 'basic':
            return False
        raw = base64.b64decode(encoded, validate=True)
        expected = (os.environ.get('FINRESEARCH_ACCESS_USER', 'owner') + ':' + password).encode('utf-8')
        return hmac.compare_digest(raw, expected)
    except (ValueError, binascii.Error):
        return False
