from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    Itinerary,
    TokenStatsResponse,
    TripDetailResponse,
    TripEditRequest,
    TripListResponse,
    TripRequest,
    TripSaveRequest,
)
from app.services.city_registry_service import CityCoverageTier
from app.services.city_resolver_service import (
    CityResolutionUnavailableError,
    resolve_city,
)
from app.services.place_candidate_service import (
    CandidateCollectionUnavailableError,
    PlaceCandidateCategory,
    collect_city_candidate_pool,
)
from app.services.storage_service import (
    delete_itinerary_by_trip_id,
    get_itinerary_by_trip_id,
    get_token_stats,
    list_saved_itineraries,
    save_itinerary,
)
from app.services.trip_service import (
    edit_trip_itinerary,
    generate_dynamic_trip_itinerary,
    generate_trip_itinerary,
)
from app.agents.graph.graph import run_trip_graph


router = APIRouter(prefix="/trip", tags=["trip"])


@router.get("", response_model=TripListResponse)
def list_trips() -> TripListResponse:
    """返回已保存行程的摘要列表。"""
    return list_saved_itineraries()


@router.post("/generate", response_model=Itinerary)
def generate_trip(request: TripRequest) -> Itinerary:
    """生成结构化 itinerary。"""
    try:
        city_resolution = resolve_city(request.destination)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_destination",
                "message": str(exc),
            },
        ) from exc
    except CityResolutionUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "city_resolution_unavailable",
                "message": str(exc),
                "reason": exc.reason,
            },
        ) from exc

    if city_resolution.tier is CityCoverageTier.INSUFFICIENT_DATA:
        is_province_scope = (
            city_resolution.resolution_reason == "province_requires_city"
        )
        province_example = (
            "，例如输入“西宁”"
            if "青海" in city_resolution.city
            else ""
        )
        raise HTTPException(
            status_code=422,
            detail={
                "code": (
                    "unsupported_destination_scope"
                    if is_province_scope
                    else "insufficient_city_data"
                ),
                "message": (
                    (
                        f"“{city_resolution.city}”是省级目的地，当前版本支持单城市规划。"
                        f"请输入省内具体城市{province_example}后重试。"
                    )
                    if is_province_scope
                    else (
                        f"暂时无法确认“{city_resolution.city}”是可规划的旅游目的地，"
                        "请检查城市名称后重试。"
                    )
                ),
                "destination": city_resolution.city,
                "coverage_tier": city_resolution.tier.value,
                "administrative_level": city_resolution.administrative_level,
            },
        )

    if city_resolution.tier is CityCoverageTier.DYNAMIC:
        try:
            candidate_pool = collect_city_candidate_pool(
                city=city_resolution.city,
                adcode=city_resolution.adcode,
                administrative_level=city_resolution.administrative_level,
            )
        except CandidateCollectionUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "candidate_collection_unavailable",
                    "message": str(exc),
                    "destination": city_resolution.city,
                    "reason": exc.reason,
                    "category": exc.category,
                },
            ) from exc

        candidate_counts = {
            category.value: len(candidate_pool.candidates_for(category))
            for category in PlaceCandidateCategory
        }
        minimum_counts = {
            category.value: minimum
            for category, minimum in candidate_pool.minimum_counts.items()
        }
        if not candidate_pool.meets_minimum:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "insufficient_candidate_data",
                    "message": (
                        f"“{city_resolution.city}”的可验证地点候选不足，"
                        "暂时无法生成可靠行程。"
                    ),
                    "destination": city_resolution.city,
                    "coverage_tier": city_resolution.tier.value,
                    "candidate_counts": candidate_counts,
                    "minimum_counts": minimum_counts,
                    "shortages": {
                        category.value: shortage
                        for category, shortage in candidate_pool.shortages.items()
                    },
                },
            )

        normalized_request = request.model_copy(
            update={"destination": city_resolution.city},
        )
        return generate_dynamic_trip_itinerary(
            normalized_request,
            candidate_pool,
        )

    normalized_request = request.model_copy(
        update={"destination": city_resolution.city},
    )
    return generate_trip_itinerary(normalized_request)


@router.post("/generate-graph", response_model=Itinerary)
def generate_trip_graph(request: TripRequest) -> Itinerary:
    """基于 LangGraph Multi-Agent 的行程生成。"""
    result = run_trip_graph({
        "destination": request.destination,
        "start_date": request.start_date.isoformat() if hasattr(request.start_date, 'isoformat') else str(request.start_date),
        "end_date": request.end_date.isoformat() if hasattr(request.end_date, 'isoformat') else str(request.end_date),
        "travelers": request.travelers,
        "budget": request.budget,
        "preferences": request.preferences,
        "pace": request.pace,
        "hotel_level": request.hotel_level,
        "dietary_preferences": request.dietary_preferences,
        "special_notes": request.special_notes,
    })

    errors = result.get("planner_errors", [])
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"code": "generation_failed", "message": "; ".join(errors)},
        )

    # Router 判定为 unsupported
    resolver_msg = result.get("resolution_message")
    if resolver_msg:
        raise HTTPException(
            status_code=422,
            detail={"code": "unsupported_destination", "message": resolver_msg},
        )

    itinerary = result.get("enriched_itinerary")
    if not itinerary:
        raise HTTPException(
            status_code=500,
            detail={"code": "empty_result", "message": "行程生成为空"},
        )
    return Itinerary(**itinerary)


@router.get("/stats", response_model=TokenStatsResponse)
def get_trip_token_stats() -> TokenStatsResponse:
    """返回所有已保存行程的 token 消耗统计。"""
    return get_token_stats()


@router.post("/edit", response_model=Itinerary)
def edit_trip(request: TripEditRequest) -> Itinerary:
    """根据用户编辑指令返回更新后的 itinerary。"""
    return edit_trip_itinerary(request)


@router.post("/save")
def save_trip(request: TripSaveRequest) -> dict[str, str]:
    """保存 itinerary，并返回 trip_id。"""
    saved_trip_id = save_itinerary(request.itinerary)
    return {
        "message": "Trip itinerary saved successfully.",
        "trip_id": saved_trip_id,
    }


@router.get("/{trip_id}", response_model=TripDetailResponse)
def get_trip_detail(trip_id: str) -> TripDetailResponse:
    """根据 trip_id 查询已保存 itinerary。"""
    trip_detail = get_itinerary_by_trip_id(trip_id)
    if trip_detail is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return trip_detail


@router.delete("/{trip_id}")
def delete_trip(trip_id: str) -> dict[str, str]:
    """根据 trip_id 删除已保存 itinerary。"""
    deleted = delete_itinerary_by_trip_id(trip_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return {
        "message": "Trip itinerary deleted successfully.",
        "trip_id": trip_id,
    }
