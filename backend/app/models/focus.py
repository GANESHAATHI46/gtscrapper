from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field

# ==========================================
# India Django Bulk Import Models
# ==========================================

class IndiaRegion(BaseModel):
    name: str
    slug: str

class IndiaCity(BaseModel):
    region: str  # region slug
    name: str
    slug: str

class IndiaPackageType(BaseModel):
    name: str
    slug: str
    is_active: bool = True

class IndiaPackageImage(BaseModel):
    image: str
    is_primary: bool = False
    sort_order: int = 1

class IndiaItineraryItem(BaseModel):
    day: int
    title: str = ""
    description: str = ""

class IndiaPackage(BaseModel):
    city: str  # city slug
    package_type: str  # package_type slug
    name: str
    slug: str
    duration: Optional[str] = None
    tour_type: Optional[str] = None
    group_size: Optional[Union[int, str]] = None
    language: Optional[str] = None
    destination: Optional[str] = None
    price: Optional[float] = None
    image: Optional[str] = None  # banner_image becomes image
    is_featured: bool = False
    is_active: bool = True
    images: List[IndiaPackageImage] = Field(default_factory=list)
    itinerary: List[IndiaItineraryItem] = Field(default_factory=list)

class IndiaBulkImportPayload(BaseModel):
    regions: List[IndiaRegion] = Field(default_factory=list)
    cities: List[IndiaCity] = Field(default_factory=list)
    package_types: List[IndiaPackageType] = Field(default_factory=list)
    packages: List[IndiaPackage] = Field(default_factory=list)


# ==========================================
# International Django Bulk Import Models
# ==========================================

class InternationalRegion(BaseModel):
    name: str
    slug: str

class InternationalCountry(BaseModel):
    region: str  # region slug
    name: str
    slug: str
    banner_image: Optional[str] = None
    is_active: bool = True

class InternationalPackageType(BaseModel):
    name: str
    slug: str
    description: str = ""

class InternationalPackageImage(BaseModel):
    image: str
    alt_text: str = ""
    display_order: int = 1
    is_active: bool = True

class InternationalItineraryItem(BaseModel):
    day_number: int
    title: str = ""
    description: str = ""
    display_order: int = 1
    is_active: bool = True

class InternationalGroup(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_seats: Optional[int] = None
    booked_seats: Optional[int] = None
    is_sold_out: bool = False
    is_active: bool = True

class InternationalPackage(BaseModel):
    country: str  # country slug
    package_type: str  # package_type slug
    name: str
    slug: str
    duration: Optional[str] = None
    tour_type: Optional[str] = None
    group_size: Optional[Union[int, str]] = None
    language: Optional[str] = None
    destination: Optional[str] = None
    price: Optional[float] = None
    banner_image: Optional[str] = None
    is_featured: bool = False
    is_active: bool = True
    groups: List[InternationalGroup] = Field(default_factory=list)
    images: List[InternationalPackageImage] = Field(default_factory=list)
    itinerary: List[InternationalItineraryItem] = Field(default_factory=list)

class InternationalBulkImportPayload(BaseModel):
    regions: List[InternationalRegion] = Field(default_factory=list)
    countries: List[InternationalCountry] = Field(default_factory=list)
    package_types: List[InternationalPackageType] = Field(default_factory=list)
    packages: List[InternationalPackage] = Field(default_factory=list)

# Aliases for convenience
IntlRegion = InternationalRegion
IntlCountry = InternationalCountry
IntlPackageType = InternationalPackageType
IntlPackageImage = InternationalPackageImage
IntlItineraryItem = InternationalItineraryItem
IntlGroup = InternationalGroup
IntlPackage = InternationalPackage
IntlBulkImportPayload = InternationalBulkImportPayload
