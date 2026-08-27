"""Odoo 19 pilot connector.

CUSTOMER #001 currently uses XML-RPC because that is what is live in the deployed
self-hosted stack. Keep this adapter behind Finance Core and migrate to JSON-2
before Odoo 22 compatibility becomes a requirement.
"""
import xmlrpc.client

class OdooClient:
    def __init__(self, url, db, login, password):
        self.url=url.rstrip('/'); self.db=db; self.login=login; self.password=password
        self.common=xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
        self.models=xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)
        self.uid=None
    def auth(self):
        self.uid=self.uid or self.common.authenticate(self.db,self.login,self.password,{})
        if not self.uid: raise RuntimeError('Odoo authentication failed')
        return self.uid
    def call(self, model, method, args=None, kwargs=None):
        return self.models.execute_kw(self.db,self.auth(),self.password,model,method,args or [],kwargs or {})
