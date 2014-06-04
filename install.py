import time

_config_template = """
{
    "server": {
        "host": "localhost",
        "port": 8999
    },
    "partners": [
        {
            "id": "partner_id",
            "token": "md5_hash"
        },
        {
            "id": "partner2_id",
            "token": "md5_hash"
        }
    ],

    "openerp": {
        "host"     : "localhost",
        "port"     : 8069,
        "database" : "database",
        "user"     : "user",
        "password" : "password"
    },

    "edi_routing" : [
        {
            "path": "/edi/purchaseOrder",
            "flow": "edi_thr_purchase_order_in"
        },
        {
            "path": "/edi/saleOrder",
            "flow": "edi_spree_sale_order_in"
        }
    ]
}
"""

def log(message):
    print time.asctime(), message



if __name__ == '__main__':

    log("Installing the Webdust EDI recipient server.")

    try:
        with open("config.json", "w") as f:
            f.write(_config_template)
        log("Server is installed, please configure config.json.")
    except Exception as e:
        log("Installation failed, error given: {!s}".format(str(e)))
        exit()







