"""Synthetic demo order fixtures for Swiggy Instamart.

Provides realistic staple orders across dates to test price timeline analysis,
pack-size normalization, and inflation alert flags offline without live network tokens.
Every staple has multi-order historical observations to enable rich trajectory curves.
"""

from typing import Any, Dict, List

DEMO_ORDERS: List[Dict[str, Any]] = [
    {
        "orderId": "SWG_IM_1001",
        "status": "DELIVERED",
        "createdAt": "2026-10-10T09:30:00Z",
        "totalAmount": 1004.00,
        "items": [
            {"name": "Fortune Sunlite Refined Sunflower Oil 1 L", "quantity": 1, "finalPrice": 165.00, "removed": False},
            {"name": "Aashirvaad Superior MP Sharbati Atta 5 kg", "quantity": 1, "finalPrice": 235.00, "removed": False},
            {"name": "Amul Taaza Homogenised Toned Milk 500 ml", "quantity": 1, "finalPrice": 27.00, "removed": False},
            {"name": "Amul Butter Pasteurized 100 g (Pack of 2)", "quantity": 1, "finalPrice": 102.00, "removed": False},
            {"name": "Tata Salt Vacuum Evaporated Iodised Salt 1 kg", "quantity": 1, "finalPrice": 25.00, "removed": False},
            {"name": "Surf Excel Matic Front Load Liquid Detergent Pouch 2 L + 1 L Free", "quantity": 1, "finalPrice": 420.00, "removed": False},
        ],
        "bill": {
            "grandTotal": "1004.00",
            "lineItems": [
                {"name": "Fortune Sunlite Refined Sunflower Oil 1 L", "amount": "165.00"},
                {"name": "Aashirvaad Superior MP Sharbati Atta 5 kg", "amount": "235.00"},
                {"name": "Amul Taaza Homogenised Toned Milk 500 ml", "amount": "27.00"},
                {"name": "Amul Butter Pasteurized 100 g (Pack of 2)", "amount": "102.00"},
                {"name": "Tata Salt Vacuum Evaporated Iodised Salt 1 kg", "amount": "25.00"},
                {"name": "Surf Excel Matic Front Load Liquid Detergent Pouch 2 L + 1 L Free", "amount": "420.00"},
            ]
        }
    },
    {
        "orderId": "SWG_IM_1002",
        "status": "DELIVERED",
        "createdAt": "2026-10-15T14:15:00Z",
        "totalAmount": 1089.00,
        "items": [
            {"name": "Fortune Sunlite Refined Sunflower Oil 1 L", "quantity": 1, "finalPrice": 172.00, "removed": False},
            {"name": "Fortune Sunlite Refined Sunflower Oil 500 ml", "quantity": 1, "finalPrice": 88.00, "removed": False},
            {"name": "Aashirvaad Superior MP Sharbati Atta 5 kg", "quantity": 1, "finalPrice": 235.00, "removed": False},
            {"name": "Amul Taaza Homogenised Toned Milk 500 ml", "quantity": 1, "finalPrice": 28.00, "removed": False},
            {"name": "Amul Butter Pasteurized 100 g (Pack of 2)", "quantity": 1, "finalPrice": 105.00, "removed": False},
            {"name": "Tata Salt Vacuum Evaporated Iodised Salt 1 kg", "quantity": 1, "finalPrice": 26.00, "removed": False},
            {"name": "Surf Excel Matic Front Load Liquid Detergent Pouch 2 L + 1 L Free", "quantity": 1, "finalPrice": 435.00, "removed": False},
        ],
        "bill": {
            "grandTotal": "1089.00",
            "lineItems": [
                {"name": "Fortune Sunlite Refined Sunflower Oil 1 L", "amount": "172.00"},
                {"name": "Fortune Sunlite Refined Sunflower Oil 500 ml", "amount": "88.00"},
                {"name": "Aashirvaad Superior MP Sharbati Atta 5 kg", "amount": "235.00"},
                {"name": "Amul Taaza Homogenised Toned Milk 500 ml", "amount": "28.00"},
                {"name": "Amul Butter Pasteurized 100 g (Pack of 2)", "amount": "105.00"},
                {"name": "Tata Salt Vacuum Evaporated Iodised Salt 1 kg", "amount": "26.00"},
                {"name": "Surf Excel Matic Front Load Liquid Detergent Pouch 2 L + 1 L Free", "amount": "435.00"},
            ]
        }
    },
    {
        "orderId": "SWG_IM_1003",
        "status": "DELIVERED",
        "createdAt": "2026-10-20T11:45:00Z",
        "totalAmount": 1131.00,
        "items": [
            {"name": "Fortune Sunlite Refined Sunflower Oil 1 L", "quantity": 1, "finalPrice": 178.00, "removed": False},
            {"name": "Fortune Sunlite Refined Sunflower Oil 500 ml", "quantity": 1, "finalPrice": 95.00, "removed": False},
            {"name": "Aashirvaad Superior MP Sharbati Atta 5 kg", "quantity": 1, "finalPrice": 245.00, "removed": False},
            {"name": "Amul Taaza Homogenised Toned Milk 500 ml", "quantity": 1, "finalPrice": 28.00, "removed": False},
            {"name": "Amul Butter Pasteurized 100 g (Pack of 2)", "quantity": 1, "finalPrice": 108.00, "removed": False},
            {"name": "Tata Salt Vacuum Evaporated Iodised Salt 1 kg", "quantity": 1, "finalPrice": 26.00, "removed": False},
            {"name": "Surf Excel Matic Front Load Liquid Detergent Pouch 2 L + 1 L Free", "quantity": 1, "finalPrice": 450.00, "removed": False},
        ],
        "bill": {
            "grandTotal": "1131.00",
            "lineItems": [
                {"name": "Fortune Sunlite Refined Sunflower Oil 1 L", "amount": "178.00"},
                {"name": "Fortune Sunlite Refined Sunflower Oil 500 ml", "amount": "95.00"},
                {"name": "Aashirvaad Superior MP Sharbati Atta 5 kg", "amount": "245.00"},
                {"name": "Amul Taaza Homogenised Toned Milk 500 ml", "amount": "28.00"},
                {"name": "Amul Butter Pasteurized 100 g (Pack of 2)", "amount": "108.00"},
                {"name": "Tata Salt Vacuum Evaporated Iodised Salt 1 kg", "amount": "26.00"},
                {"name": "Surf Excel Matic Front Load Liquid Detergent Pouch 2 L + 1 L Free", "amount": "450.00"},
            ]
        }
    },
    {
        "orderId": "SWG_IM_1004",
        "status": "DELIVERED",
        "createdAt": "2026-10-24T18:20:00Z",
        "totalAmount": 1205.00,
        "items": [
            {"name": "Fortune Sunlite Refined Sunflower Oil 1 L", "quantity": 1, "finalPrice": 185.00, "removed": False},
            {"name": "Fortune Sunlite Refined Sunflower Oil 500 ml", "quantity": 1, "finalPrice": 98.00, "removed": False},
            {"name": "Aashirvaad Superior MP Sharbati Atta 5 kg", "quantity": 1, "finalPrice": 255.00, "removed": False},
            {"name": "Amul Taaza Homogenised Toned Milk 500 ml", "quantity": 1, "finalPrice": 29.00, "removed": False},
            {"name": "Amul Butter Pasteurized 100 g (Pack of 2)", "quantity": 1, "finalPrice": 112.00, "removed": False},
            {"name": "Tata Salt Vacuum Evaporated Iodised Salt 1 kg", "quantity": 1, "finalPrice": 28.00, "removed": False},
            {"name": "Surf Excel Matic Front Load Liquid Detergent Pouch 2 L + 1 L Free", "quantity": 1, "finalPrice": 475.00, "removed": False},
        ],
        "bill": {
            "grandTotal": "1205.00",
            "lineItems": [
                {"name": "Fortune Sunlite Refined Sunflower Oil 1 L", "amount": "185.00"},
                {"name": "Fortune Sunlite Refined Sunflower Oil 500 ml", "amount": "98.00"},
                {"name": "Aashirvaad Superior MP Sharbati Atta 5 kg", "amount": "255.00"},
                {"name": "Amul Taaza Homogenised Toned Milk 500 ml", "amount": "29.00"},
                {"name": "Amul Butter Pasteurized 100 g (Pack of 2)", "amount": "112.00"},
                {"name": "Tata Salt Vacuum Evaporated Iodised Salt 1 kg", "amount": "28.00"},
                {"name": "Surf Excel Matic Front Load Liquid Detergent Pouch 2 L + 1 L Free", "amount": "475.00"},
            ]
        }
    }
]
