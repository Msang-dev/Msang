from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Optional
from uuid import uuid4


class Farmer(BaseModel):
    farmer_id: str
    name: str
    village: str
    tea_variety: str


class CollectionInput(BaseModel):
    farmer_id: str
    kilograms: float = Field(gt=0)
    leaf_temperature_c: float = Field(ge=0, le=45)
    moisture_percent: float = Field(ge=40, le=90)


class CollectionRecord(BaseModel):
    collection_id: str
    farmer_id: str
    farmer_name: str
    village: str
    kilograms: float
    leaf_temperature_c: float
    moisture_percent: float
    timestamp: str
    quality_flag: str


class ProcessingInput(BaseModel):
    collection_ids: List[str] = Field(min_length=1)
    stage: str = Field(description="withering | rolling | oxidation | drying | sorting")
    machine_line: str
    stage_temperature_c: float
    duration_minutes: int = Field(gt=0)


class QualityAssessmentInput(BaseModel):
    batch_id: str
    liquor_color_score: float = Field(ge=0, le=10)
    aroma_score: float = Field(ge=0, le=10)
    moisture_percent: float = Field(ge=0, le=10)
    particle_uniformity_percent: float = Field(ge=0, le=100)
    contamination_incidents: int = Field(ge=0)


class AuctionSaleInput(BaseModel):
    lot_id: str
    buyer_name: str
    grade: str
    kilograms: float = Field(gt=0)
    price_per_kg_usd: float = Field(gt=0)


INTERNATIONAL_TEA_STANDARDS: Dict[str, Dict[str, float]] = {
    "moisture_percent": {"max": 3.0},
    "particle_uniformity_percent": {"min": 85.0},
    "liquor_color_score": {"min": 7.5},
    "aroma_score": {"min": 7.0},
    "contamination_incidents": {"max": 0},
}


def classify_leaf_quality(moisture_percent: float, leaf_temperature_c: float) -> str:
    if moisture_percent >= 75 and leaf_temperature_c <= 24:
        return "excellent"
    if moisture_percent >= 68 and leaf_temperature_c <= 28:
        return "good"
    return "watch"


class KapkorosTeaFactorySystem:
    def __init__(self) -> None:
        self.farmers: Dict[str, Farmer] = {
            "F001": Farmer(farmer_id="F001", name="Mary Chebet", village="Kapkoros", tea_variety="TRFK 6/8"),
            "F002": Farmer(farmer_id="F002", name="Joel Kiprotich", village="Boito", tea_variety="TRFK 31/8"),
            "F003": Farmer(farmer_id="F003", name="Agnes Ngetich", village="Kipsigis", tea_variety="TRFK 91/1"),
        }
        self.collections: Dict[str, CollectionRecord] = {}
        self.processing_batches: Dict[str, dict] = {}
        self.quality_assessments: Dict[str, dict] = {}
        self.inventory_lots: Dict[str, dict] = {}
        self.sales: List[dict] = []

    def add_collection(self, payload: CollectionInput) -> CollectionRecord:
        farmer = self.farmers.get(payload.farmer_id)
        if not farmer:
            raise HTTPException(status_code=404, detail="Farmer not found")

        collection = CollectionRecord(
            collection_id=f"COL-{uuid4().hex[:8].upper()}",
            farmer_id=farmer.farmer_id,
            farmer_name=farmer.name,
            village=farmer.village,
            kilograms=payload.kilograms,
            leaf_temperature_c=payload.leaf_temperature_c,
            moisture_percent=payload.moisture_percent,
            timestamp=datetime.utcnow().isoformat(),
            quality_flag=classify_leaf_quality(payload.moisture_percent, payload.leaf_temperature_c),
        )
        self.collections[collection.collection_id] = collection
        return collection

    def add_processing_batch(self, payload: ProcessingInput) -> dict:
        valid_stages = {"withering", "rolling", "oxidation", "drying", "sorting"}
        if payload.stage not in valid_stages:
            raise HTTPException(status_code=400, detail=f"Stage must be one of: {', '.join(sorted(valid_stages))}")

        linked_records = []
        for cid in payload.collection_ids:
            record = self.collections.get(cid)
            if not record:
                raise HTTPException(status_code=404, detail=f"Collection ID not found: {cid}")
            linked_records.append(record)

        total_input = round(sum(x.kilograms for x in linked_records), 2)
        expected_output = round(total_input * 0.23, 2)

        batch_id = f"BAT-{uuid4().hex[:8].upper()}"
        batch = {
            "batch_id": batch_id,
            "collection_ids": payload.collection_ids,
            "stage": payload.stage,
            "machine_line": payload.machine_line,
            "stage_temperature_c": payload.stage_temperature_c,
            "duration_minutes": payload.duration_minutes,
            "input_kilograms": total_input,
            "expected_made_tea_kilograms": expected_output,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.processing_batches[batch_id] = batch

        lot_id = f"LOT-{uuid4().hex[:8].upper()}"
        self.inventory_lots[lot_id] = {
            "lot_id": lot_id,
            "batch_id": batch_id,
            "grade": "BP1",
            "available_kilograms": expected_output,
            "status": "ready_for_auction",
            "created_at": datetime.utcnow().isoformat(),
        }
        batch["lot_id"] = lot_id
        return batch

    def assess_quality(self, payload: QualityAssessmentInput) -> dict:
        batch = self.processing_batches.get(payload.batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")

        checks = {
            "liquor_color_score": payload.liquor_color_score >= INTERNATIONAL_TEA_STANDARDS["liquor_color_score"]["min"],
            "aroma_score": payload.aroma_score >= INTERNATIONAL_TEA_STANDARDS["aroma_score"]["min"],
            "moisture_percent": payload.moisture_percent <= INTERNATIONAL_TEA_STANDARDS["moisture_percent"]["max"],
            "particle_uniformity_percent": payload.particle_uniformity_percent >= INTERNATIONAL_TEA_STANDARDS["particle_uniformity_percent"]["min"],
            "contamination_incidents": payload.contamination_incidents <= INTERNATIONAL_TEA_STANDARDS["contamination_incidents"]["max"],
        }
        passed = all(checks.values())

        assessment = {
            "assessment_id": f"QA-{uuid4().hex[:8].upper()}",
            "batch_id": payload.batch_id,
            "scores": payload.model_dump(),
            "checks": checks,
            "compliance_status": "pass" if passed else "fail",
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.quality_assessments[payload.batch_id] = assessment
        return assessment

    def record_sale(self, payload: AuctionSaleInput) -> dict:
        lot = self.inventory_lots.get(payload.lot_id)
        if not lot:
            raise HTTPException(status_code=404, detail="Lot not found")
        if payload.kilograms > lot["available_kilograms"]:
            raise HTTPException(status_code=400, detail="Sale kilograms exceed available inventory")

        lot["available_kilograms"] = round(lot["available_kilograms"] - payload.kilograms, 2)
        if lot["available_kilograms"] == 0:
            lot["status"] = "sold_out"

        sale = {
            "sale_id": f"SAL-{uuid4().hex[:8].upper()}",
            "lot_id": payload.lot_id,
            "buyer_name": payload.buyer_name,
            "grade": payload.grade,
            "kilograms": payload.kilograms,
            "price_per_kg_usd": payload.price_per_kg_usd,
            "total_value_usd": round(payload.kilograms * payload.price_per_kg_usd, 2),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.sales.append(sale)
        return sale

    def traceability_report(self) -> List[dict]:
        report = []
        for lot in self.inventory_lots.values():
            batch = self.processing_batches.get(lot["batch_id"], {})
            collections = [self.collections[cid].model_dump() for cid in batch.get("collection_ids", []) if cid in self.collections]
            qa = self.quality_assessments.get(lot["batch_id"])
            lot_sales = [s for s in self.sales if s["lot_id"] == lot["lot_id"]]
            report.append(
                {
                    "lot": lot,
                    "batch": batch,
                    "collections": collections,
                    "quality_assessment": qa,
                    "sales": lot_sales,
                }
            )
        return report

    def dashboard(self) -> dict:
        total_collected = round(sum(c.kilograms for c in self.collections.values()), 2)
        total_made_tea = round(sum(x["expected_made_tea_kilograms"] for x in self.processing_batches.values()), 2)
        total_sales = round(sum(x["total_value_usd"] for x in self.sales), 2)
        compliance_rate = 0.0
        if self.quality_assessments:
            passes = sum(1 for x in self.quality_assessments.values() if x["compliance_status"] == "pass")
            compliance_rate = round((passes / len(self.quality_assessments)) * 100, 2)

        return {
            "factory": "Kapkoros Tea Factory",
            "international_standard": "ISO 3720-inspired quality thresholds",
            "metrics": {
                "registered_farmers": len(self.farmers),
                "collections_recorded": len(self.collections),
                "processing_batches": len(self.processing_batches),
                "inventory_lots": len(self.inventory_lots),
                "sales_transactions": len(self.sales),
                "total_green_leaf_collected_kg": total_collected,
                "expected_made_tea_kg": total_made_tea,
                "auction_revenue_usd": total_sales,
                "quality_compliance_rate_percent": compliance_rate,
            },
            "international_standards": INTERNATIONAL_TEA_STANDARDS,
        }


system = KapkorosTeaFactorySystem()

app = FastAPI(title="Kapkoros Tea Factory Management API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {
        "message": "Kapkoros Tea Factory Software Management System",
        "modules": [
            "farmer_collection",
            "processing_monitoring",
            "quality_compliance",
            "traceability",
            "auction_sales",
        ],
    }


@app.get("/farmers", response_model=List[Farmer])
def list_farmers() -> List[Farmer]:
    return list(system.farmers.values())


@app.post("/collections", response_model=CollectionRecord)
def create_collection(payload: CollectionInput) -> CollectionRecord:
    return system.add_collection(payload)


@app.get("/collections", response_model=List[CollectionRecord])
def list_collections() -> List[CollectionRecord]:
    return list(system.collections.values())


@app.post("/processing")
def create_processing_batch(payload: ProcessingInput) -> dict:
    return system.add_processing_batch(payload)


@app.get("/processing")
def list_processing_batches() -> List[dict]:
    return list(system.processing_batches.values())


@app.post("/quality-assessments")
def create_quality_assessment(payload: QualityAssessmentInput) -> dict:
    return system.assess_quality(payload)


@app.get("/quality-assessments")
def list_quality_assessments() -> List[dict]:
    return list(system.quality_assessments.values())


@app.get("/inventory")
def list_inventory() -> List[dict]:
    return list(system.inventory_lots.values())


@app.post("/auction-sales")
def create_auction_sale(payload: AuctionSaleInput) -> dict:
    return system.record_sale(payload)


@app.get("/auction-sales")
def list_auction_sales() -> List[dict]:
    return system.sales


@app.get("/traceability")
def get_traceability_report() -> List[dict]:
    return system.traceability_report()


@app.get("/dashboard")
def get_dashboard() -> dict:
    return system.dashboard()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
