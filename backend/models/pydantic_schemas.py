from typing import Optional, Any

class BaseModel:
    """
    Custom BaseModel implementation mimicking Pydantic v2.
    Allows dynamic filtering of fields for role-based serialization,
    supporting type annotations and extra fields when allowed.
    """
    def __init__(self, **data):
        annotations = {}
        # Collect all type annotations from current class and its base classes
        for cls in self.__class__.__mro__:
            annotations.update(getattr(cls, '__annotations__', {}))
            
        config = getattr(self, 'Config', None)
        allow_extra = False
        if config and getattr(config, 'extra', None) == "allow":
            allow_extra = True
            
        self._data = {}
        for key, val in data.items():
            if key in annotations:
                self._data[key] = val
            elif allow_extra:
                self._data[key] = val
                
        # Ensure default values or None are populated for declared fields if not in data
        for key in annotations:
            if key not in self._data:
                if hasattr(self.__class__, key):
                    self._data[key] = getattr(self.__class__, key)
                else:
                    self._data[key] = None

    def model_dump(self, *args, **kwargs) -> dict:
        """Returns validated dictionary containing only schema fields."""
        return self._data

    def dict(self, *args, **kwargs) -> dict:
        """Compatibility function mimicking Pydantic v1 dict()."""
        return self._data


# ─── SUPPLIER RESPONSE SCHEMAS ───────────────────────────────────────────────

class SupplierPublic(BaseModel):
    supplier_id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    status: Optional[str] = None
    currency: Optional[str] = None


class SupplierAdmin(BaseModel):
    supplier_id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    status: Optional[str] = None
    currency: Optional[str] = None
    reliability_score: Optional[float] = None
    avg_delay_days: Optional[float] = None
    on_time_rate: Optional[float] = None
    total_sales: Optional[float] = None
    total_revenue: Optional[float] = None
    total_profit: Optional[float] = None
    composite_score: Optional[float] = None

    class Config:
        extra = "allow"


# ─── PRODUCT RESPONSE SCHEMAS ────────────────────────────────────────────────

class ProductPublic(BaseModel):
    product_id: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    product_name: str
    product_price: Optional[float] = None
    product_status: Optional[str] = None
    description: Optional[str] = None
    currency: Optional[str] = None


class ProductAdmin(BaseModel):
    product_id: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    product_name: str
    product_price: Optional[float] = None
    product_status: Optional[str] = None
    description: Optional[str] = None
    currency: Optional[str] = None
    cost: Optional[float] = None
    margin: Optional[float] = None
    profit: Optional[float] = None
    revenue: Optional[float] = None
    sales: Optional[float] = None

    class Config:
        extra = "allow"


# ─── ORDER RESPONSE SCHEMAS ──────────────────────────────────────────────────

class OrderPublic(BaseModel):
    order_id: int
    customer_id: Optional[int] = None
    customer_fname: Optional[str] = None
    customer_lname: Optional[str] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    sales: Optional[float] = None
    profit: Optional[float] = None
    order_date: Optional[str] = None
    order_status: Optional[str] = None
    payment_type: Optional[str] = None
    shipment: Optional[Any] = None
    currency: Optional[str] = None


class OrderAdmin(BaseModel):
    order_id: int
    customer_id: Optional[int] = None
    customer_fname: Optional[str] = None
    customer_lname: Optional[str] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    sales: Optional[float] = None
    profit: Optional[float] = None
    order_date: Optional[str] = None
    order_status: Optional[str] = None
    payment_type: Optional[str] = None
    shipment: Optional[Any] = None
    currency: Optional[str] = None
    unit_price: Optional[float] = None
    total_cost: Optional[float] = None
    transportation_cost: Optional[float] = None

    class Config:
        extra = "allow"


# ─── SHIPMENT RESPONSE SCHEMAS ───────────────────────────────────────────────

class ShipmentPublic(BaseModel):
    shipment_id: int
    order_id: Optional[int] = None
    shipping_date: Optional[str] = None
    shipping_mode: Optional[str] = None
    days_shipping_real: Optional[int] = None
    days_shipment_scheduled: Optional[int] = None
    delivery_status: Optional[str] = None
    late_delivery_risk: Optional[int] = None


class ShipmentAdmin(BaseModel):
    shipment_id: int
    order_id: Optional[int] = None
    shipping_date: Optional[str] = None
    shipping_mode: Optional[str] = None
    days_shipping_real: Optional[int] = None
    days_shipment_scheduled: Optional[int] = None
    delivery_status: Optional[str] = None
    late_delivery_risk: Optional[int] = None
    unit_price: Optional[float] = None
    total_cost: Optional[float] = None
    transportation_cost: Optional[float] = None

    class Config:
        extra = "allow"
