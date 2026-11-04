from pathlib import Path
import json
import re
import pandas as pd
import nbformat

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DD_DIR = ROOT / "docs" / "data_dictionary"
KPI_DIR = ROOT / "docs" / "kpi_definitions"
CHUNK_SIZE = 50000

SOURCES = {
    "Listings": RAW_DIR / "listings.csv.gz",
    "Calendar": RAW_DIR / "calendar.csv.gz",
    "Reviews": RAW_DIR / "reviews.csv.gz",
    "Neighbourhoods": RAW_DIR / "neighbourhoods.csv",
}

# Đọc metadata để xác định snapshot_date của từng nguồn
INVENTORY_PATH = ROOT / "docs" / "source_inventory.csv"

if not INVENTORY_PATH.exists():
    raise FileNotFoundError(
        f"Không tìm thấy source_inventory.csv: {INVENTORY_PATH}"
    )

SOURCE_INVENTORY = pd.read_csv(
    INVENTORY_PATH,
    encoding="utf-8-sig"
)

# Kiểm tra các cột metadata bắt buộc
required_inventory_columns = {"file_name", "snapshot_date"}

if not required_inventory_columns.issubset(SOURCE_INVENTORY.columns):
    raise ValueError(
        "source_inventory.csv thiếu cột file_name hoặc snapshot_date."
    )

# Xác định snapshot_date cho từng file RAW
SNAPSHOT_BY_FILE = {}

for source_name, source_path in SOURCES.items():

    matched_dates = (
        SOURCE_INVENTORY.loc[
            SOURCE_INVENTORY["file_name"].astype("string").str.strip()
            == source_path.name,
            "snapshot_date"
        ]
        .dropna()
        .astype("string")
        .str.strip()
        .unique()
    )

    if len(matched_dates) != 1:
        raise ValueError(
            f"Không xác định được duy nhất snapshot_date cho "
            f"{source_path.name}: {matched_dates}"
        )

    SNAPSHOT_BY_FILE[source_path.name] = pd.to_datetime(
        matched_dates[0],
        errors="raise"
    ).strftime("%Y-%m-%d")

print("[INFO] Snapshot metadata:", SNAPSHOT_BY_FILE)


MEANINGS = {
    "id": "Mã định danh duy nhất của tin đăng Airbnb.",
    "listing_url": "Đường dẫn trang tin đăng trên Airbnb.",
    "scrape_id": "Mã lần thu thập dữ liệu của nguồn.",
    "last_scraped": "Ngày tin đăng được thu thập lần cuối.",
    "source": "Nguồn hoặc trạng thái xuất xứ của bản ghi theo dữ liệu Inside Airbnb.",
    "name": "Tên hiển thị của tin đăng.",
    "description": "Nội dung mô tả chi tiết tin đăng.",
    "neighborhood_overview": "Mô tả tổng quan về khu vực xung quanh tin đăng.",
    "picture_url": "Đường dẫn hình ảnh đại diện của tin đăng.",
    "host_id": "Mã định danh của chủ nhà.",
    "host_url": "Đường dẫn hồ sơ chủ nhà trên Airbnb.",
    "host_profile_id": "Mã hồ sơ chủ nhà theo hệ thống nguồn.",
    "host_profile_url": "Đường dẫn hồ sơ chủ nhà theo hệ thống nguồn.",
    "host_name": "Tên hiển thị của chủ nhà.",
    "host_since": "Ngày chủ nhà bắt đầu tham gia Airbnb.",
    "hosts_time_as_user_years": "Số năm chủ nhà đã tham gia Airbnb với tư cách người dùng.",
    "hosts_time_as_user_months": "Số tháng lẻ chủ nhà đã tham gia Airbnb với tư cách người dùng.",
    "hosts_time_as_host_years": "Số năm chủ nhà đã hoạt động với tư cách chủ nhà.",
    "hosts_time_as_host_months": "Số tháng lẻ chủ nhà đã hoạt động với tư cách chủ nhà.",
    "host_location": "Địa điểm được khai báo trong hồ sơ chủ nhà.",
    "host_about": "Phần giới thiệu về chủ nhà.",
    "host_response_time": "Khoảng thời gian phản hồi tin nhắn của chủ nhà theo phân loại nguồn.",
    "host_response_rate": "Tỷ lệ phản hồi của chủ nhà.",
    "host_acceptance_rate": "Tỷ lệ chấp nhận yêu cầu đặt chỗ của chủ nhà.",
    "host_is_superhost": "Cho biết chủ nhà có trạng thái Superhost hay không.",
    "host_thumbnail_url": "Đường dẫn ảnh thu nhỏ trong hồ sơ chủ nhà.",
    "host_picture_url": "Đường dẫn ảnh hồ sơ chủ nhà.",
    "host_neighbourhood": "Khu vực được ghi nhận trong hồ sơ chủ nhà.",
    "host_listings_count": "Số tin đăng của chủ nhà theo thông tin hồ sơ.",
    "host_total_listings_count": "Tổng số tin đăng của chủ nhà theo thông tin nguồn.",
    "host_verifications": "Các phương thức xác minh được ghi nhận cho chủ nhà.",
    "host_has_profile_pic": "Cho biết hồ sơ chủ nhà có ảnh đại diện hay không.",
    "host_identity_verified": "Cho biết danh tính chủ nhà đã được xác minh hay chưa.",
    "neighbourhood": "Tên khu vực địa lý được ghi nhận trong dữ liệu nguồn.",
    "neighbourhood_cleansed": "Tên khu vực của tin đăng sau chuẩn hóa theo Inside Airbnb; dùng để liên kết danh mục khu vực.",
    "neighbourhood_group_cleansed": "Nhóm khu vực địa lý đã được chuẩn hóa.",
    "latitude": "Vĩ độ vị trí tin đăng.",
    "longitude": "Kinh độ vị trí tin đăng.",
    "property_type": "Loại hình cơ sở lưu trú hoặc bất động sản.",
    "room_type": "Loại hình không gian cho thuê (toàn bộ nhà/căn hộ, phòng riêng, phòng chung hoặc phòng khách sạn).",
    "accommodates": "Số khách tối đa mà tin đăng có thể tiếp nhận.",
    "bathrooms": "Số phòng tắm được ghi nhận dưới dạng số.",
    "bathrooms_text": "Mô tả số lượng hoặc loại phòng tắm dưới dạng văn bản.",
    "bedrooms": "Số phòng ngủ.",
    "beds": "Số giường.",
    "amenities": "Danh sách tiện nghi được cung cấp.",
    "price": "Giá niêm yết cho một đêm lưu trú của tin đăng tại thời điểm thu thập dữ liệu. Đơn vị tiền tệ được xác định dựa trên thông tin báo giá của nguồn.",
    "price_quote_checkin_date": "Ngày nhận phòng dùng để tạo báo giá tham chiếu trong dữ liệu nguồn.",
    "price_quote_checkout_date": "Ngày trả phòng dùng để tạo báo giá tham chiếu trong dữ liệu nguồn.",
    "price_quote_total_price": "Tổng giá báo tham chiếu cho khoảng lưu trú được ghi trong dữ liệu nguồn.",
    "price_quote_price_per_night": "Giá mỗi đêm trong báo giá tham chiếu của nguồn.",
    "price_quote_raw": "Dữ liệu báo giá gốc dạng JSON, có thể chứa mã tiền tệ và thông tin giá.",
    "minimum_nights": "Số đêm lưu trú tối thiểu được yêu cầu.",
    "maximum_nights": "Số đêm lưu trú tối đa được phép.",
    "minimum_minimum_nights": "Giá trị tối thiểu của số đêm lưu trú tối thiểu trong các cấu hình được tổng hợp.",
    "maximum_minimum_nights": "Giá trị tối đa của số đêm lưu trú tối thiểu trong các cấu hình được tổng hợp.",
    "minimum_maximum_nights": "Giá trị tối thiểu của số đêm lưu trú tối đa trong các cấu hình được tổng hợp.",
    "maximum_maximum_nights": "Giá trị tối đa của số đêm lưu trú tối đa trong các cấu hình được tổng hợp.",
    "minimum_nights_avg_ntm": "Số đêm lưu trú tối thiểu trung bình trong khoảng thời gian tiếp theo theo định nghĩa nguồn.",
    "maximum_nights_avg_ntm": "Số đêm lưu trú tối đa trung bình trong khoảng thời gian tiếp theo theo định nghĩa nguồn.",
    "calendar_updated": "Thời điểm cập nhật lịch theo thông tin nguồn.",
    "has_availability": "Cho biết tin đăng có thông tin về tình trạng sẵn có hay không.",
    "availability_30": "Số ngày còn khả dụng trong 30 ngày tiếp theo tính từ thời điểm chụp dữ liệu.",
    "availability_60": "Số ngày còn khả dụng trong 60 ngày tiếp theo tính từ thời điểm chụp dữ liệu.",
    "availability_90": "Số ngày còn khả dụng trong 90 ngày tiếp theo tính từ thời điểm chụp dữ liệu.",
    "availability_365": "Số ngày còn khả dụng trong 365 ngày tiếp theo tính từ thời điểm chụp dữ liệu.",
    "calendar_last_scraped": "Ngày lịch của tin đăng được thu thập lần cuối.",
    "number_of_reviews": "Tổng số lượt đánh giá được ghi nhận cho tin đăng tại thời điểm chụp dữ liệu.",
    "number_of_reviews_ltm": "Số lượt đánh giá được ghi nhận trong 12 tháng gần nhất theo dữ liệu nguồn.",
    "number_of_reviews_l30d": "Số lượt đánh giá được ghi nhận trong 30 ngày gần nhất theo dữ liệu nguồn.",
    "availability_eoy": "Số ngày hoặc trạng thái còn khả dụng đến cuối năm theo cách tổng hợp của nguồn.",
    "number_of_reviews_ly": "Số lượt đánh giá được ghi nhận trong năm trước theo dữ liệu nguồn.",
    "estimated_occupancy_l365d": "Ước tính mức độ lấp đầy trong 365 ngày gần nhất do nguồn cung cấp; không phải số lượt đặt phòng được quan sát trực tiếp.",
    "estimated_revenue_l365d": "Ước tính doanh thu trong 365 ngày gần nhất do nguồn cung cấp; không phải doanh thu giao dịch được xác thực.",
    "first_review": "Ngày đăng đánh giá đầu tiên được ghi nhận cho tin đăng.",
    "last_review": "Ngày đăng đánh giá gần nhất được ghi nhận cho tin đăng.",
    "review_scores_rating": "Điểm đánh giá tổng thể của tin đăng theo thang điểm nguồn.",
    "review_scores_accuracy": "Điểm đánh giá về độ chính xác của mô tả tin đăng.",
    "review_scores_cleanliness": "Điểm đánh giá về mức độ sạch sẽ.",
    "review_scores_checkin": "Điểm đánh giá về quy trình nhận phòng.",
    "review_scores_communication": "Điểm đánh giá về giao tiếp với chủ nhà.",
    "review_scores_location": "Điểm đánh giá về vị trí.",
    "review_scores_value": "Điểm đánh giá về mức độ tương xứng giữa chất lượng và chi phí.",
    "license": "Mã hoặc thông tin giấy phép, đăng ký được chủ nhà khai báo cho tin đăng.",
    "instant_bookable": "Cho biết tin đăng có hỗ trợ đặt phòng ngay hay không.",
    "calculated_host_listings_count": "Số tin đăng của chủ nhà được tính theo phương pháp của nguồn.",
    "calculated_host_listings_count_entire_homes": "Số tin đăng toàn bộ nhà hoặc căn hộ của chủ nhà theo nguồn.",
    "calculated_host_listings_count_private_rooms": "Số tin đăng phòng riêng của chủ nhà theo nguồn.",
    "calculated_host_listings_count_shared_rooms": "Số tin đăng phòng chung của chủ nhà theo nguồn.",
    "reviews_per_month": "Số lượt đánh giá trung bình mỗi tháng theo cách tính của nguồn.",
    "available": "Trạng thái còn khả dụng của tin đăng trong ngày lịch; t là còn khả dụng, f là không còn khả dụng.",
    "date": "Ngày áp dụng của bản ghi.",
    "reviewer_id": "Mã định danh của người viết đánh giá.",
    "reviewer_name": "Tên hiển thị của người viết đánh giá.",
    "comments": "Nội dung văn bản đánh giá do người dùng gửi.",
    "neighbourhood_group": "Nhóm hoặc vùng địa lý chứa khu vực."
}

def meaning_for(source, col):
    # Cùng tên cột nhưng ý nghĩa thay đổi theo nguồn/grain.
    source_specific = {
        ("Listings", "id"): "Mã định danh duy nhất của tin đăng Airbnb.",
        ("Reviews", "id"): "Mã định danh của bản ghi đánh giá trong nguồn Reviews.",
        ("Calendar", "date"): "Ngày lịch mà trạng thái khả dụng của listing được ghi nhận.",
        ("Reviews", "date"): "Ngày bản ghi đánh giá được đăng/ghi nhận.",
        ("Calendar", "listing_id"): "Mã tin đăng mà bản ghi lịch trong ngày thuộc về.",
        ("Reviews", "listing_id"): "Mã tin đăng được người dùng đánh giá.",
        ("Reviews", "reviewer_id"): "Mã định danh của người viết đánh giá.",

        ("Listings", "price"): (
            "Giá niêm yết cho một đêm lưu trú của tin đăng "
            "tại thời điểm thu thập dữ liệu; đơn vị tiền tệ "
            "được xác định qua thông tin báo giá của nguồn."
        ),
        ("Calendar", "date"): (
            "Ngày lịch mà trạng thái còn khả dụng của tin đăng "
            "được ghi nhận."
        ),
        ("Calendar", "minimum_nights"): (
            "Số đêm lưu trú tối thiểu áp dụng cho tin đăng "
            "trong ngày lịch."
        ),
        ("Calendar", "maximum_nights"): (
            "Số đêm lưu trú tối đa được phép đối với tin đăng "
            "trong ngày lịch."
        ),
        ("Listings", "neighbourhood_cleansed"): "Tên khu vực của tin đăng đã được chuẩn hóa theo dữ liệu Inside Airbnb; dùng để đối chiếu với danh mục khu vực.",
    }
    if (source, col) in source_specific:
        return source_specific[(source, col)]
    if col in MEANINGS:
        return MEANINGS[col]
    # Cách diễn đạt dự phòng vẫn bằng tiếng Việt, không để nguyên cụm tiếng Anh kiểu "Trường dữ liệu mô tả..."
    label = col.replace("_", " ").strip()
    return f"Thông tin {label} của {source}, theo trường dữ liệu do Inside Airbnb cung cấp."

def clean_sample(v):
    if pd.isna(v): return ""
    s = str(v).replace("\r"," ").replace("\n"," ").strip()
    return s[:180] + ("..." if len(s)>180 else "")


def key_role(source, col):

    if source == "Listings" and col == "id":
        return (
            "Khóa định danh của listing; "
            "khi tích hợp nhiều snapshot trong Warehouse, "
            "cần kết hợp snapshot_date để phân biệt các lần thu thập."
        )

    if source == "Calendar" and col == "listing_id":
        return "Khóa ngoại dự kiến tham chiếu Listings.id."

    if source == "Calendar" and col == "date":
        return (
            "Thành phần khóa của dữ liệu RAW; "
            "kết hợp listing_id để xác định một listing tại một ngày "
            "trong file snapshot. Khi tích hợp nhiều snapshot trong "
            "Warehouse, bổ sung snapshot_date."
        )

    if source == "Reviews" and col == "id":
        return (
            "Mã review nguồn; cần kiểm tra trùng và kết hợp listing_id "
            "để xác định bản ghi đánh giá."
        )

    if source == "Reviews" and col == "listing_id":
        return "Khóa ngoại dự kiến tham chiếu Listings.id."

    if (
            source == "Neighbourhoods"
            and col in {"neighbourhood_group", "neighbourhood"}
    ):
        return (
            "Thành phần khóa ghép dự kiến "
            "(neighbourhood_group, neighbourhood) "
            "của danh mục khu vực."
        )
    if source == "Listings" and col == "neighbourhood_cleansed":
        return "Khóa ngoại dự kiến tham chiếu Neighbourhoods.neighbourhood."

    return "Không phải khóa chính/khóa ngoại đã xác nhận."


# Kiểu nghiệp vụ độc lập với dtype suy đoán từ CSV, nhất là cột toàn NULL.
DATE_COLUMNS = {"date", "last_scraped", "calendar_last_scraped", "host_since",
                "first_review", "last_review", "price_quote_checkin_date",
                "price_quote_checkout_date"}
BOOLEAN_COLUMNS = {"available", "host_is_superhost", "host_has_profile_pic",
                   "host_identity_verified", "has_availability", "instant_bookable"}
TEXT_COLUMNS = {"host_response_time", "neighbourhood", "host_neighbourhood",
                "neighbourhood_cleansed", "neighbourhood_group_cleansed",
                "neighbourhood_group", "host_thumbnail_url", "calendar_updated"}
INTEGER_COLUMNS = {"accommodates", "bedrooms", "beds", "host_listings_count",
                   "host_total_listings_count", "minimum_nights", "maximum_nights",
                   "minimum_minimum_nights", "maximum_minimum_nights",
                   "minimum_maximum_nights", "maximum_maximum_nights",
                   "hosts_time_as_user_years", "hosts_time_as_user_months",
                   "hosts_time_as_host_years", "hosts_time_as_host_months"}


def transformation(col, dtype):
    c = col.lower()
    if c in {"id", "listing_id", "reviewer_id", "host_id", "host_profile_id", "scrape_id"}:
        return "Lưu BIGINT; giữ chính xác chữ số, không chuyển ID sang số thực."
    if c in DATE_COLUMNS:
        return "Chuẩn hóa thành DATE; giữ NULL; ghi nhận giá trị không parse được."
    if c in BOOLEAN_COLUMNS:
        return "Chuẩn hóa t/true/1 thành TRUE, f/false/0 thành FALSE; giữ NULL và báo giá trị ngoài miền."
    if c == "price":
        return "Parse giá sang DECIMAL; giữ NULL; chỉ đưa vào KPI giá khi quote.currency trong price_quote_raw xác định là SGD."
    if c == "price_quote_raw":
        return "Giữ JSON gốc để truy vết; kiểm tra parse JSON và trích quote.currency khi cần."
    if c in {"price_quote_total_price", "price_quote_price_per_night"}:
        return "Lưu DECIMAL; giữ NULL và thông tin currency; đây là báo giá tham chiếu, không phải doanh thu."
    if c == "host_verifications" or c == "amenities":
        return "Giữ TEXT/JSON gốc; chỉ parse danh sách sau kiểm tra cấu trúc; không suy kiểu số từ cột toàn NULL."
    if c in TEXT_COLUMNS or c.endswith("_url"):
        return "Lưu VARCHAR/TEXT; chuẩn hóa khoảng trắng và NULL; không suy kiểu số từ dtype của cột toàn NULL."
    if c in INTEGER_COLUMNS or c.startswith(("number_of_reviews", "calculated_host_listings_count", "availability_")):
        return "Lưu số nguyên có thể NULL; kiểm tra tính nguyên và miền không âm; không làm tròn giá trị không hợp lệ."
    if c in {"minimum_nights_avg_ntm", "maximum_nights_avg_ntm", "bathrooms", "reviews_per_month"}:
        return "Lưu DECIMAL với precision/scale phù hợp; giữ phần thập phân và NULL."
    if c.startswith("review_scores_"):
        return "Lưu DECIMAL; kiểm tra miền quan sát 1–5 của snapshot; giữ NULL, không thay bằng 0."
    if c in {"host_response_rate", "host_acceptance_rate"}:
        return "Parse phần trăm sang DECIMAL theo đơn vị 0–100; giữ NULL; kiểm tra ký hiệu % và miền giá trị."
    if c in {"latitude", "longitude"}:
        return "Lưu DECIMAL với độ chính xác phù hợp; kiểm tra miền tọa độ."
    if c in {"comments", "description", "host_about", "neighborhood_overview"}:
        return "Giữ TEXT và NULL; không suy ra điểm review từ nội dung văn bản."
    if dtype.startswith("int"):
        return "Lưu INT/BIGINT đủ miền giá trị; xác minh đơn vị và miền nghiệp vụ trước khi dùng."
    if dtype.startswith("float"):
        return "Lưu DECIMAL nếu trường có ý nghĩa số; giữ NULL và xác nhận kiểu nghiệp vụ trước khi nạp đích."
    return "Lưu VARCHAR/TEXT; chuẩn hóa khoảng trắng và NULL theo quy tắc đã duyệt."

def inspect_source(name, path):
    if not path.exists(): raise FileNotFoundError(f"Thiếu file nguồn: {path}")
    snapshot_date = SNAPSHOT_BY_FILE[path.name]
    rows=0; dtypes={}; nulls={}; samples={}; categorical={}
    dates={}
    for chunk in pd.read_csv(path, compression="infer", encoding="utf-8-sig", chunksize=CHUNK_SIZE, low_memory=False):
        rows += len(chunk)
        for c in chunk.columns:
            if c not in dtypes:
                dtypes[c]=str(chunk[c].dtype); nulls[c]=0; samples[c]=""
            nulls[c]+=int(chunk[c].isna().sum())
            if not samples[c]:
                vals=chunk[c].dropna()
                if len(vals): samples[c]=clean_sample(vals.iloc[0])
            if c.lower() in DATE_COLUMNS:
                d=pd.to_datetime(chunk[c],errors="coerce").dropna()
                if len(d):
                    if c not in dates: dates[c]=[d.min(),d.max()]
                    else: dates[c]=[min(dates[c][0],d.min()),max(dates[c][1],d.max())]
            if c in {"available","room_type"}:
                vc=chunk[c].dropna().astype(str).value_counts()
                for val,n in vc.items(): categorical.setdefault(c,{})[val]=categorical.setdefault(c,{}).get(val,0)+int(n)
    out=[]
    for c,dtype in dtypes.items():
        null_n=nulls[c]
        extra=""
        if c in dates: extra=f"Ngày quan sát: {dates[c][0].date()} đến {dates[c][1].date()}."
        if c in categorical:
            extra += " Giá trị quan sát: " + "; ".join(f"{v} ({n:,})" for v,n in sorted(categorical[c].items(),key=lambda x:-x[1]))
        out.append({
            "source_name":name,"source_file":path.name,"column_name":c,
            "business_meaning":meaning_for(name,c),"initial_pandas_dtype":dtype,
            "sample_value":samples[c],"row_count_source":rows,"null_count":null_n,
            "null_rate_percent":round(null_n/rows*100,4) if rows else 0,
            "nullable_observed":"Có NULL" if null_n else "Không phát hiện NULL",
            "key_role":key_role(name,c),"proposed_transformation":transformation(c,dtype),
            "kpi_relevance": "Trường dùng trực tiếp/hỗ trợ KPI hoặc liên kết" if c in {
                "id","listing_id","date","available","price","price_quote_raw","price_quote_price_per_night",
                "room_type","review_scores_rating","number_of_reviews","neighbourhood_cleansed",
                "neighbourhood_group_cleansed","neighbourhood","neighbourhood_group"
            } else "Trường mô tả/hỗ trợ kiểm tra; chưa dùng trực tiếp trong KPI cốt lõi",
            "observed_range_or_values":extra
        })

    summary = {
        "source_name": name,
        "source_file": path.name,
        "snapshot_date": snapshot_date,
        "row_count": rows,
        "column_count": len(dtypes),
        "grain": {
            "Listings": "Một listing tại một snapshot",
            "Calendar": "Một listing tại một ngày lịch và một snapshot",
            "Reviews": "Một bản ghi đánh giá",
            "Neighbourhoods": "Một khu vực"
        }[name]
    }

    return out, summary


def build_dictionary():
    DD_DIR.mkdir(parents=True,exist_ok=True)
    all_rows=[]; summaries=[]
    for name,path in SOURCES.items():
        rows,summary=inspect_source(name,path); all_rows.extend(rows); summaries.append(summary)
        pd.DataFrame(rows).to_csv(DD_DIR/f"data_dictionary_{name.lower()}.csv",index=False,encoding="utf-8-sig")
    df=pd.DataFrame(all_rows)
    df.to_csv(DD_DIR/"data_dictionary_all_sources.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(summaries).to_csv(DD_DIR/"source_profile_for_dictionary.csv",index=False,encoding="utf-8-sig")
    (DD_DIR/"README.md").write_text("""# Data Dictionary – Airbnb Singapore (Task 2.2)

Các CSV được sinh trực tiếp từ bốn file trong `data/raw/`. `business_meaning` được diễn đạt thống nhất bằng tiếng Việt. `initial_pandas_dtype` là kiểu Pandas đọc từ CSV, không phải kiểu dữ liệu cuối cùng trong MySQL. `key_role` chỉ nêu khóa dự kiến; cần kiểm thử trước khi áp constraint. Script không chỉnh sửa dữ liệu raw.
""",encoding="utf-8")
    return df

BUSINESS_KPIS = [
{"kpi_id":"KPI-01","kpi_name":"Số listing duy nhất theo snapshot","business_definition":"Số lượng mã listing phân biệt được ghi nhận trong một file Listings thuộc snapshot được chọn.","source_fields":"Listings.id; Listings.scrape_id; Listings.last_scraped","formula":"COUNT(DISTINCT id)","filters":"Chỉ dùng một snapshot; loại id NULL; xác nhận snapshot theo scrape_id và metadata nguồn. Với file hiện tại, scrape_id = 20260923225116; last_scraped quan sát từ 2026-09-25 đến 2026-09-26.","numerator":"Số mã listing duy nhất hợp lệ.","denominator":"Không áp dụng.","unit":"Listing","grain":"Một listing tại snapshot","interpretation":"Quy mô tin đăng được ghi nhận tại snapshot, không phải số listing còn available trong một ngày.","caveats":"Không đếm dòng Calendar/Reviews; không gộp nhiều snapshot nếu chưa có quy tắc chọn snapshot."},
{"kpi_id":"KPI-02","kpi_name":"Trung vị giá niêm yết mỗi đêm","business_definition":"Trung vị giá niêm yết mỗi đêm của các listing có giá hợp lệ và xác định được tiền tệ SGD tại snapshot.","source_fields":"Listings.id; Listings.price; Listings.price_quote_raw; Listings.price_quote_price_per_night","formula":"MEDIAN(price_clean), mỗi listing một lần; price_clean chỉ nhận khi quote.currency = 'SGD'.","filters":"Một snapshot; price không NULL, parse được, hữu hạn và > 0; trích currency từ quote.currency trong price_quote_raw; loại bản ghi không xác định được currency; đối chiếu price với price_quote_price_per_night.","numerator":"Không áp dụng cho median.","denominator":"Không áp dụng; báo cáo coverage = listing có giá SGD hợp lệ / tổng listing snapshot.","unit":"SGD/đêm","grain":"Một listing tại snapshot","interpretation":"Một nửa listing có giá hợp lệ có giá không lớn hơn median và một nửa không nhỏ hơn median.","caveats":"Trong dữ liệu hiện tại có 2.855 báo giá ghi rõ currency=SGD; 35 báo giá không có currency trong JSON. Không suy luận SGD chỉ từ ký hiệu '$'. Giá niêm yết/báo giá không phải giá giao dịch hay doanh thu."},
{"kpi_id":"KPI-03","kpi_name":"Tỷ trọng loại phòng","business_definition":"Tỷ lệ listing thuộc từng room_type trên tổng listing có room_type hợp lệ trong cùng snapshot và phạm vi lọc.","source_fields":"Listings.id; Listings.room_type; Listings.neighbourhood_cleansed","formula":"Số listing duy nhất thuộc room_type X / tổng listing duy nhất có room_type hợp lệ × 100%.","filters":"Giữ bộ lọc snapshot và khu vực; khi tính tỷ trọng trong khu vực, bỏ riêng bộ lọc room_type ở mẫu số; chỉ nhận room_type không NULL/rỗng và mỗi id một lần.","numerator":"Số listing duy nhất thuộc room_type X trong phạm vi đang xét.","denominator":"Tổng listing duy nhất có room_type hợp lệ trong cùng phạm vi snapshot/khu vực; không áp bộ lọc room_type vào mẫu số.","unit":"% listing","grain":"Một listing tại snapshot","interpretation":"Mô tả cơ cấu loại phòng trong tổng tin đăng có phân loại của phạm vi đang xét.","caveats":"Không dùng số dòng Calendar/Reviews làm mẫu số. Nếu một id có nhiều room_type xung đột, đưa vào kiểm tra thay vì tự chọn."},
{"kpi_id":"KPI-04","kpi_name":"Tỷ lệ bản ghi lịch còn available","business_definition":"Tỷ lệ bản ghi listing-ngày có trạng thái available trong tổng bản ghi listing-ngày có trạng thái hợp lệ.","source_fields":"Calendar.listing_id; Calendar.date; Calendar.available","formula":"SUM(CASE WHEN available = TRUE THEN 1 ELSE 0 END) / SUM(CASE WHEN available IN (TRUE,FALSE) THEN 1 ELSE 0 END) × 100%. Tử số là số dòng thỏa điều kiện, không viết COUNT(điều kiện).","filters":"listing_id và date hợp lệ; available chuẩn hóa thành TRUE/FALSE; kiểm tra và xử lý duplicate theo (listing_id,date) trong file RAW hiện tại vì chỉ có một snapshot; khi tích hợp nhiều snapshot trong Warehouse, grain gồm thêm snapshot_date; so sánh các khu vực và room_type trên cùng cửa sổ ngày 2026-09-25 đến 2027-09-25.","numerator":"Số dòng listing-ngày hợp lệ có available = TRUE.","denominator":"Số dòng listing-ngày hợp lệ có available = TRUE hoặc FALSE trong cùng cửa sổ ngày.","unit":"% bản ghi listing-ngày","grain":"Một listing tại một ngày lịch và một snapshot","interpretation":"Tỷ lệ trạng thái lịch được đánh dấu còn khả dụng trong cùng khoảng thời gian quan sát.","caveats":"FALSE chỉ là không khả dụng, không chứng minh đã có booking. Không gọi là occupancy rate. Chỉ so sánh nhóm trên cùng cửa sổ ngày; loại trùng theo grain trước khi tính."},
{"kpi_id":"KPI-05","kpi_name":"Điểm review tổng thể trung bình","business_definition":"Điểm review tổng thể trung bình giữa các listing có review_scores_rating hợp lệ tại snapshot; mỗi listing có trọng số bằng nhau.","source_fields":"Listings.id; Listings.review_scores_rating","formula":"AVG(review_scores_rating) trên mỗi listing duy nhất có điểm hợp lệ.","filters":"Một snapshot; điểm là số hữu hạn trong miền 1–5; loại NULL; mỗi listing tính một lần.","numerator":"Tổng điểm review tổng thể của các listing có điểm hợp lệ.","denominator":"Số listing duy nhất có điểm review tổng thể hợp lệ.","unit":"Điểm (thang quan sát 1–5)","grain":"Một listing tại snapshot","interpretation":"Điểm tổng thể trung bình giữa các listing có điểm, không phải trung bình của từng review trong Reviews.","caveats":"Dữ liệu snapshot hiện tại quan sát được miền 1–5; xác nhận lại với metadata của phiên bản nguồn. Không thay NULL bằng 0; công bố coverage."},
{"kpi_id":"SUP-01","kpi_name":"Trung vị số review trên mỗi listing","business_definition":"Trung vị số review được ghi nhận trên mỗi listing tại snapshot.","source_fields":"Listings.id; Listings.number_of_reviews","formula":"MEDIAN(number_of_reviews), mỗi listing một lần.","filters":"Một snapshot; number_of_reviews là số hợp lệ và không âm; giữ giá trị 0; không thay NULL bằng 0.","numerator":"Không áp dụng.","denominator":"Không áp dụng.","unit":"Review/listing","grain":"Một listing tại snapshot","interpretation":"Mức số lượng review điển hình của listing trong nhóm đang phân tích.","caveats":"Không thay NULL bằng 0; không mặc định số dòng Reviews luôn bằng number_of_reviews nếu chưa đối chiếu cùng snapshot/phạm vi."},
{"kpi_id":"SUP-02","kpi_name":"Số bản ghi review trong kỳ","business_definition":"Số bản ghi review hợp lệ được ghi nhận trong khoảng ngày được chọn.","source_fields":"Reviews.listing_id; Reviews.id; Reviews.date","formula":"Đếm bản ghi theo khóa (listing_id, id) sau kiểm tra trùng; lọc date trong khoảng chọn.","filters":"Ngày review hợp lệ và nằm trong kỳ; listing_id hợp lệ; kiểm tra trùng khóa ghép (listing_id,id); không đếm DISTINCT id riêng nếu id có thể trùng giữa listing.","numerator":"Số bản ghi review hợp lệ trong kỳ.","denominator":"Không áp dụng.","unit":"Bản ghi review","grain":"Một bản ghi review","interpretation":"Lượng review quan sát được trong kỳ, có thể phân tích theo thời gian/khu vực/loại phòng sau khi liên kết listing đúng grain.","caveats":"Không suy ra số booking; không coi review date là ngày đặt phòng; Reviews.id hiện có trùng lặp nên dùng khóa ghép sau khi kiểm tra."},
]

TECH_KPIS = [
{"technical_kpi_id":"TQ-01","technical_kpi_name":"Tỷ lệ thiếu dữ liệu (Missing Value Rate)","definition":"Tỷ lệ ô NULL/thiếu trên tổng số ô thuộc danh sách trường bắt buộc được kiểm tra.","formula":"Tổng số ô NULL ở các trường bắt buộc / tổng số ô được kiểm tra × 100%.","scope":"Báo cáo theo từng trường và tổng hợp theo nguồn/lớp dữ liệu; danh sách trường bắt buộc phải được nhóm chốt trước.","unit":"%","grain":"Một trường dữ liệu trong một nguồn/lớp và snapshot","interpretation":"Tỷ lệ càng thấp cho thấy mức độ đầy đủ càng cao; phải xem cùng số dòng và mức độ quan trọng của trường.","caveats":"Không gộp mọi cột tùy ý; phân biệt NULL hợp lệ (ví dụ comments có thể thiếu) với NULL ở trường bắt buộc."},
{"technical_kpi_id":"TQ-02","technical_kpi_name":"Số bản ghi trùng khóa (Duplicate Key Count)","definition":"Số bản ghi vượt quá một bản ghi duy nhất theo khóa và grain đã xác định.","formula":"COUNT(rows) - COUNT(DISTINCT business_key) hoặc số dòng bị đánh dấu duplicate theo khóa/grain.","scope":"Kiểm tra RAW hiện tại (một snapshot): Listings dùng id; Calendar dùng (listing_id,date); Reviews dùng (listing_id,id) sau xác minh; Neighbourhoods dùng khóa ghép (neighbourhood_group,neighbourhood). Khi tích hợp nhiều snapshot trong Warehouse, Calendar sử dụng (listing_id,date,snapshot_date).","unit":"Bản ghi trùng","grain":"Theo khóa/grain của từng nguồn/lớp","interpretation":"Giá trị 0 nghĩa là không phát hiện bản ghi trùng theo khóa kiểm tra.","caveats":"Không mặc định Reviews.id riêng là duy nhất; phải nêu rõ khóa và quy tắc giữ/xử lý bản ghi trùng."},
{"technical_kpi_id":"TQ-03","technical_kpi_name":"Tỷ lệ toàn vẹn tham chiếu (Referential Integrity Rate)","definition":"Tỷ lệ bản ghi con có khóa tham chiếu tồn tại trong bảng cha tương ứng.","formula":"Số bản ghi con có khóa cha hợp lệ / tổng bản ghi con có khóa cần liên kết × 100%.","scope":"Calendar.listing_id và Reviews.listing_id tham chiếu Listings.id; Listings sử dụng cặp (neighbourhood_group_cleansed, neighbourhood_cleansed) để tham chiếu cặp (neighbourhood_group, neighbourhood) trong Neighbourhoods.","unit":"%","grain":"Bản ghi cần liên kết của từng quan hệ","interpretation":"Tỷ lệ càng cao cho thấy liên kết giữa các nguồn càng đầy đủ.","caveats":"Báo cáo riêng số khóa NULL và số khóa mồ côi; không gộp hai loại thành cùng một lỗi."},
{"technical_kpi_id":"TQ-04","technical_kpi_name":"Tỷ lệ bản ghi hợp lệ (Valid Record Rate)","definition":"Tỷ lệ bản ghi đáp ứng toàn bộ quy tắc chất lượng bắt buộc đã được phê duyệt.","formula":"Số bản ghi đạt tất cả kiểm tra bắt buộc / tổng số bản ghi được kiểm tra × 100%.","scope":"Kiểm tra kiểu dữ liệu, miền giá trị, trường bắt buộc, khóa/grain, ngày và quy tắc nghiệp vụ tại từng lớp raw/staging/Silver/Gold.","unit":"%","grain":"Một bản ghi tại từng nguồn/lớp","interpretation":"Đo tỷ lệ dữ liệu đáp ứng tiêu chí sử dụng sau kiểm tra.","caveats":"Công bố rõ rule và số dòng bị loại/sửa; không làm tỷ lệ tăng giả tạo bằng cách âm thầm xóa bản ghi."},
{"technical_kpi_id":"TQ-05","technical_kpi_name":"Tính nhất quán khi chạy lại pipeline (Pipeline Re-run Consistency)","definition":"Mức độ giống nhau của số lượng bản ghi và KPI đầu ra khi chạy lại pipeline với cùng dữ liệu nguồn, cấu hình và snapshot.","formula":"So sánh row count và KPI sau lần chạy lại với lần chạy chuẩn; PASS khi các giá trị bằng nhau trong sai số/độ chính xác đã quy định và không phát sinh bản ghi trùng.","scope":"Thực hiện tối thiểu hai lần chạy cùng snapshot; đối chiếu raw→staging→Silver→Gold, log và kết quả KPI.","unit":"PASS/FAIL và chênh lệch bản ghi/KPI","grain":"Một lần chạy pipeline cho một snapshot","interpretation":"PASS chứng minh pipeline có thể tái hiện kết quả với cùng đầu vào.","caveats":"Không thể tính từ file raw đơn lẻ; phải chạy pipeline ETL thực tế ít nhất hai lần và lưu log/đối chiếu."},
]

def write_kpis():
    KPI_DIR.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(BUSINESS_KPIS).to_csv(KPI_DIR/"kpi_definitions.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(TECH_KPIS).to_csv(KPI_DIR/"technical_kpi_definitions.csv",index=False,encoding="utf-8-sig")
    lines=["# Định nghĩa KPI – Airbnb Singapore (Task 2.2)","","## Quy ước chung",
    "- Phạm vi chính là một snapshot Listings; file hiện tại có scrape_id `20260923225116`, trong khi last_scraped quan sát từ `2026-09-25` đến `2026-09-26`.",
    "- Grain: Listings = listing/snapshot; Calendar = listing/ngày/snapshot; Reviews = một review; Neighbourhoods = một khu vực.",
    "- KPI cấp listing tính từ Listings trước khi nối với Calendar/Reviews để tránh nhân bản.",
    "- Tập rỗng hoặc mẫu số bằng 0: trả NULL/không xác định, không trả 0%. NULL không được tự động thay bằng 0.",
    "- Giữ độ chính xác gốc khi đối chiếu; chỉ làm tròn khi trình bày: tỷ lệ 2 chữ số thập phân, giá/điểm 2 chữ số thập phân, số đếm là số nguyên.",
    "- KPI-04 so sánh các nhóm trên cùng cửa sổ ngày Calendar hiện tại: `2026-09-25` đến `2027-09-25` (366 ngày).",
    "- Currency: `price_quote_raw.quote.currency` quan sát là SGD ở 2.855 bản ghi; 35 bản ghi không có currency trong JSON nên không được mặc định SGD.",
    "- Miền điểm review_scores_rating quan sát trong snapshot là 1–5; cần đối chiếu metadata phiên bản nguồn khi chốt ETL.",
    "- Snapshot chính theo source_inventory.csv: `2026-09-23`. Đây là metadata của nguồn, không phải cột có sẵn trong các file RAW.",
    ""]
    for k in BUSINESS_KPIS:
        lines += [f"## {k['kpi_id']} – {k['kpi_name']}","",f"**Định nghĩa:** {k['business_definition']}","",
        f"**Nguồn:** {k['source_fields']}","",f"**Công thức:** {k['formula']}","",
        f"**Bộ lọc:** {k['filters']}","",f"**Tử số:** {k['numerator']}","",
        f"**Mẫu số:** {k['denominator']}","",f"**Đơn vị:** {k['unit']}","",
        f"**Grain:** {k['grain']}","",f"**Diễn giải:** {k['interpretation']}","",
        f"**Lưu ý:** {k['caveats']}",""]
    lines += ["## Technical KPI / Data Quality","",
    "Các chỉ tiêu dưới đây phải được đo ở các lớp raw/staging/Silver/Gold và lưu kết quả kiểm thử. TQ-05 chỉ xác nhận được sau khi chạy pipeline ít nhất hai lần với cùng đầu vào.",""]
    for k in TECH_KPIS:
        lines += [f"### {k['technical_kpi_id']} – {k['technical_kpi_name']}","",
        f"**Định nghĩa:** {k['definition']}","",f"**Công thức:** {k['formula']}","",
        f"**Phạm vi:** {k['scope']}","",f"**Đơn vị:** {k['unit']}","",
        f"**Grain:** {k['grain']}","",f"**Diễn giải:** {k['interpretation']}","",
        f"**Lưu ý:** {k['caveats']}",""]
    (KPI_DIR/"kpi_definitions.md").write_text("\n".join(lines),encoding="utf-8")
    (KPI_DIR/"README.md").write_text("""# KPI Definitions – Task 2.2

- `kpi_definitions.csv`: 5 Business KPI chính và 2 KPI hỗ trợ về review.
- `technical_kpi_definitions.csv`: 5 Technical KPI/Data Quality theo Scope.
- `kpi_definitions.md`: công thức, bộ lọc, tử số, mẫu số, đơn vị, grain, diễn giải và quy ước chung.

Đây là tài liệu định nghĩa, không phải kết quả KPI đã tính. TQ-05 cần được kiểm chứng bằng hai lần chạy pipeline ETL thực tế.
""",encoding="utf-8")



def _read_source(name):
    """Đọc dữ liệu raw để kiểm tra chất lượng, không chỉnh sửa file gốc."""
    path = SOURCES[name]
    return pd.read_csv(
        path,
        compression="infer",
        encoding="utf-8-sig",
        low_memory=False
    )



def _count_duplicate_excess(df, keys):
    """
    Đếm số dòng dư do trùng khóa.
    Loại các bản ghi có khóa NULL hoặc chuỗi rỗng.
    Giữ lại bản ghi đầu tiên theo từng khóa.
    """

    valid = df[keys].notna().all(axis=1)

    # Loại khóa dạng chuỗi rỗng hoặc chỉ chứa khoảng trắng
    for col in keys:

        if (
            df[col].dtype == "object"
            or pd.api.types.is_string_dtype(df[col])
        ):

            non_blank = (
                df[col]
                .astype("string")
                .str.strip()
                .ne("")
                .fillna(False)
            )

            valid &= non_blank

    if not valid.any():
        return 0, int((~valid).sum())

    duplicated = df.loc[
        valid, keys
    ].duplicated(keep="first")

    return int(duplicated.sum()), int((~valid).sum())



def build_quality_results(dictionary):
    """
    Thực hiện:
    1. Kiểm tra mô tả Data Dictionary.
    2. Kiểm tra Currency và Review Rating.
    3. Tính kết quả Technical KPI TQ-01 đến TQ-04.
    4. TQ-05 để chưa đánh giá nếu chưa có log ETL hai lần chạy.
    """

    output_dir = ROOT / "outputs" / "task_2_2"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Đọc dữ liệu từ bốn nguồn
    data = {
        name: _read_source(name)
        for name in SOURCES
    }

    # ==================================================
    # 1. KIỂM TRA MÔ TẢ DATA DICTIONARY
    # ==================================================

    audit = dictionary[
        ["source_name", "column_name", "business_meaning"]
    ].copy()

    audit["audit_status"] = "Đạt – có mô tả nghiệp vụ"

    missing = (
        audit["business_meaning"].isna()
        | audit["business_meaning"].astype(str).str.strip().eq("")
    )

    fallback_flags = []

    for row in audit.itertuples(index=False):
        generic_text = (
            f"Thông tin {str(row.column_name).replace('_', ' ').strip()} "
            f"của {row.source_name}, theo trường dữ liệu do Inside Airbnb cung cấp."
        )

        fallback_flags.append(
            str(row.business_meaning) == generic_text
        )

    fallback = pd.Series(
        fallback_flags,
        index=audit.index
    )

    audit.loc[
        missing,
        "audit_status"
    ] = "Cần bổ sung – mô tả trống"

    audit.loc[
        fallback & ~missing,
        "audit_status"
    ] = "Cần rà soát – đang dùng mô tả dự phòng"

    audit.to_csv(
        output_dir / "dictionary_meaning_audit.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # ==================================================
    # 2. KIỂM TRA CURRENCY VÀ REVIEW RATING
    # ==================================================

    listings = data["Listings"].copy()

    def extract_currency(value):
        if pd.isna(value):
            return None

        try:
            obj = json.loads(value) if isinstance(value, str) else value

            if isinstance(obj, dict):
                return obj.get("quote", {}).get("currency")

            return None

        except (ValueError, TypeError, AttributeError):
            return None

    quote_present = listings["price_quote_raw"].notna()

    currencies = listings["price_quote_raw"].map(
        extract_currency
    )

    rating = pd.to_numeric(
        listings["review_scores_rating"],
        errors="coerce"
    )

    quote_with_data = int(quote_present.sum())

    quote_without_currency = int(
        (quote_present & currencies.isna()).sum()
    )

    quote_missing = int((~quote_present).sum())

    sgd_count = int((currencies == "SGD").sum())

    other_currency = int(
        (currencies.notna() & (currencies != "SGD")).sum()
    )

    # Đối chiếu giá Listings.price với giá báo mỗi đêm
    # trong price_quote_raw.quote.price_per_night

    def extract_quote_price(value):
        if pd.isna(value):
            return None

        try:
            obj = json.loads(value) if isinstance(value, str) else value

            if isinstance(obj, dict):
                return obj.get("quote", {}).get("price_per_night")

            return None

        except (ValueError, TypeError, AttributeError):
            return None

    price_numeric = pd.to_numeric(
        listings["price"]
        .astype("string")
        .str.replace(r"[^0-9.\-]", "", regex=True),
        errors="coerce"
    )

    quote_price_numeric = pd.to_numeric(
        listings["price_quote_raw"].map(extract_quote_price),
        errors="coerce"
    )

    price_check_mask = (
        (currencies == "SGD")
        & price_numeric.notna()
        & quote_price_numeric.notna()
    )

    price_difference = (
        price_numeric - quote_price_numeric
    ).abs()

    price_match_count = int(
        (
            price_check_mask
            & (price_difference <= 0.005 + 1e-9)
        ).sum()
    )

    price_mismatch_count = int(
        (
            price_check_mask
            & (price_difference > 0.005 + 1e-9)
        ).sum()
    )


    rating_nonnull = int(rating.notna().sum())

    rating_valid = int(
        rating.between(1, 5, inclusive="both").sum()
    )

    validation_rows = [
        {
            "check_id": "SRC-01",
            "noi_dung": "Currency trong price_quote_raw.quote.currency",
            "so_ban_ghi_kiem_tra": quote_with_data,
            "ket_qua": (
                f"JSON báo giá có dữ liệu: {quote_with_data:,}; "
                f"SGD: {sgd_count:,}; "
                f"JSON có nhưng thiếu currency: {quote_without_currency:,}; "
                f"price_quote_raw NULL: {quote_missing:,}; "
                f"khác SGD: {other_currency:,}"
            ),
            "trang_thai": (
                "Chỉ xác định SGD khi currency trong JSON bằng SGD"
            )
        },
        {
            "check_id": "SRC-02",
            "noi_dung": "Miền giá trị review_scores_rating",
            "so_ban_ghi_kiem_tra": rating_nonnull,
            "ket_qua": (
                f"Min: {rating.min() if rating_nonnull else None}; "
                f"Max: {rating.max() if rating_nonnull else None}; "
                f"Hợp lệ 1–5: {rating_valid:,}; "
                f"Ngoài miền: {rating_nonnull - rating_valid:,}"
            ),
            "trang_thai": (
                "NULL không được tự động xem là điểm 0"
            )
        },
        {
            "check_id": "SRC-03",
            "noi_dung": (
                "Đối chiếu Listings.price với "
                "price_quote_price_per_night"
            ),
            "so_ban_ghi_kiem_tra": int(price_check_mask.sum()),
            "ket_qua": (
                f"Có đủ hai giá trị để đối chiếu: "
                f"{int(price_check_mask.sum()):,}; "
                f"Khớp trong sai số 0,005 SGD: "
                f"{price_match_count:,}; "
                f"Sai lệch vượt ngưỡng: "
                f"{price_mismatch_count:,}"
            ),
            "trang_thai": (
                "Chỉ đối chiếu các listing có currency SGD "
                "và đủ hai giá trị giá hợp lệ."
            )
        },
    ]

    pd.DataFrame(validation_rows).to_csv(
        output_dir / "source_validation_checks.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # ==================================================
    # 3. TQ-01: MISSING VALUE RATE
    # ==================================================

    required_fields = {
        "Listings": ["id", "scrape_id"],
        "Calendar": ["listing_id", "date", "available"],
        "Reviews": ["listing_id", "id", "date"],
        "Neighbourhoods": [
            "neighbourhood_group",
            "neighbourhood"
        ]
    }

    tq1_rows = []

    total_null = 0
    total_cells = 0

    for source, columns in required_fields.items():

        df = data[source]

        present_columns = [
            col for col in columns
            if col in df.columns
        ]

        null_count = sum(
            int(df[col].isna().sum())
            for col in present_columns
        )

        checked_cells = len(df) * len(present_columns)

        total_null += null_count
        total_cells += checked_cells

        tq1_rows.append({
            "technical_kpi_id": "TQ-01",
            "nguon": source,
            "truong_kiem_tra": ", ".join(present_columns),
            "so_dong": len(df),
            "so_o_kiem_tra": checked_cells,
            "so_o_thieu": null_count,
            "ket_qua_percent": (
                round(null_count / checked_cells * 100, 4)
                if checked_cells else None
            ),
            "ghi_chu": (
                "Chỉ tính các trường bắt buộc được khai báo "
                "trong required_fields."
            )
        })

    tq1_rows.append({
        "technical_kpi_id": "TQ-01",
        "nguon": "Tổng hợp",
        "truong_kiem_tra": "Các trường bắt buộc của 4 nguồn",
        "so_dong": None,
        "so_o_kiem_tra": total_cells,
        "so_o_thieu": total_null,
        "ket_qua_percent": (
            round(total_null / total_cells * 100, 4)
            if total_cells else None
        ),
        "ghi_chu": "Tỷ lệ tính trên tổng số ô thuộc các trường bắt buộc."
    })

    # ==================================================
    # 4. TQ-02: DUPLICATE KEY COUNT
    # ==================================================

    duplicate_specs = {
        "Listings": ["id"],
        "Calendar": ["listing_id", "date"],
        "Reviews": ["listing_id", "id"],
        "Neighbourhoods": [
            "neighbourhood_group",
            "neighbourhood"
        ]
    }

    tq2_rows = []

    for source, keys in duplicate_specs.items():

        df = data[source]

        duplicate_count, missing_key_count = (
            _count_duplicate_excess(df, keys)
        )

        tq2_rows.append({
            "technical_kpi_id": "TQ-02",
            "nguon": source,
            "khoa_grain": " + ".join(keys),
            "so_dong_nguon": len(df),
            "so_dong_trung_du": duplicate_count,
            "so_dong_thieu_thanh_phan_khoa": missing_key_count,
            "ghi_chu": (
                "Reviews dùng khóa ghép (listing_id, id), "
                "không dùng id riêng lẻ. Calendar dùng "
                "(listing_id, date) vì raw không có snapshot_date."
            )
        })

    # ==================================================
    # 5. TQ-03: REFERENTIAL INTEGRITY RATE
    # ==================================================

    parent_ids = set(
        listings["id"].dropna()
    )

    neighbourhoods = set(
        data["Neighbourhoods"]["neighbourhood"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    relations = [
        (
            "Calendar.listing_id -> Listings.id",
            data["Calendar"]["listing_id"],
            parent_ids
        ),
        (
            "Reviews.listing_id -> Listings.id",
            data["Reviews"]["listing_id"],
            parent_ids
        ),
        (
            "Listings.(neighbourhood_group_cleansed, "
            "neighbourhood_cleansed) -> "
            "Neighbourhoods.(neighbourhood_group, neighbourhood)",

            pd.Series(
                list(zip(
                    listings["neighbourhood_group_cleansed"]
                    .astype("string").str.strip(),

                    listings["neighbourhood_cleansed"]
                    .astype("string").str.strip()
                ))
            ),

            set(zip(
                data["Neighbourhoods"]["neighbourhood_group"]
                .astype("string").str.strip(),

                data["Neighbourhoods"]["neighbourhood"]
                .astype("string").str.strip()
            ))
        )
    ]

    tq3_rows = []

    for label, child, parents in relations:

        nonnull = child.map(
            lambda value: all(pd.notna(v) and str(v).strip() != "" for v in value)
            if isinstance(value, tuple)
            else pd.notna(value) and str(value).strip() != ""
        )

        values = child[nonnull]

        valid = values.isin(parents)

        tq3_rows.append({
            "technical_kpi_id": "TQ-03",
            "quan_he": label,
            "tong_dong_con": len(child),
            "khoa_con_null_or_blank": int((~nonnull).sum()),
            "khoa_con_co_gia_tri": int(nonnull.sum()),
            "khoa_mo_coi": int((~valid).sum()),
            "khoa_hop_le": int(valid.sum()),
            "ket_qua_percent": (
                round(valid.mean() * 100, 4)
                if len(values) else None
            ),
            "ghi_chu": (
                "Tỷ lệ tính trên khóa con có giá trị. "
                "NULL/rỗng và khóa mồ côi được báo cáo riêng."
            )
        })

    # ==================================================
    # 6. TQ-04: VALID RECORD RATE
    # ==================================================

    tq4_rows = []

    def add_valid(source, valid_mask, rule):

        df = data[source]

        total_rows = len(df)

        valid_rows = int(
            valid_mask.fillna(False).sum()
        )

        tq4_rows.append({
            "technical_kpi_id": "TQ-04",
            "nguon": source,
            "quy_tac_hop_le": rule,
            "so_dong": total_rows,
            "so_dong_hop_le": valid_rows,
            "so_dong_khong_hop_le": total_rows - valid_rows,
            "ket_qua_percent": (
                round(valid_rows / total_rows * 100, 4)
                if total_rows else None
            )
        })

    L = data["Listings"]
    C = data["Calendar"]
    R = data["Reviews"]
    N = data["Neighbourhoods"]

    add_valid(
        "Listings",
        (
            L["id"].notna()
            & L["scrape_id"].notna()
            & (
                rating.isna()
                | rating.between(1, 5, inclusive="both")
            )
        ),
        "id và scrape_id không NULL; rating nếu có phải thuộc miền 1–5."
    )

    calendar_date = pd.to_datetime(
        C["date"],
        errors="coerce"
    )

    available_valid = (
        C["available"]
        .astype("string")
        .str.strip()
        .str.lower()
        .isin(["t", "f", "true", "false", "1", "0"])
    )

    add_valid(
        "Calendar",
        (
            C["listing_id"].notna()
            & calendar_date.notna()
            & available_valid
        ),
        "listing_id có giá trị; date hợp lệ; available thuộc t/f/true/false/1/0."
    )

    review_date = pd.to_datetime(
        R["date"],
        errors="coerce"
    )

    add_valid(
        "Reviews",
        (
            R["listing_id"].notna()
            & R["id"].notna()
            & review_date.notna()
        ),
        "listing_id, id không NULL và date hợp lệ."
    )

    add_valid(
        "Neighbourhoods",
        (
                N["neighbourhood_group"].notna()
                & N["neighbourhood_group"]
                .astype("string")
                .str.strip()
                .ne("")
                & N["neighbourhood"].notna()
                & N["neighbourhood"]
                .astype("string")
                .str.strip()
                .ne("")
        ),
        (
            "Cả neighbourhood_group và neighbourhood "
            "đều không NULL hoặc rỗng; kiểm tra đầy đủ "
            "hai thành phần khóa ghép."
        )
    )

    # ==================================================
    # 7. XUẤT BẢNG CHI TIẾT
    # ==================================================

    details = (
        tq1_rows
        + tq2_rows
        + tq3_rows
        + tq4_rows
    )

    pd.DataFrame(details).to_csv(
        output_dir / "technical_kpi_detail.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # ==================================================
    # 8. TỔNG HỢP KẾT QUẢ TQ-01 ĐẾN TQ-05
    # ==================================================

    tq2_total = sum(
        row["so_dong_trung_du"]
        for row in tq2_rows
    )

    tq3_valid = sum(
        row["khoa_hop_le"]
        for row in tq3_rows
    )

    tq3_nonnull = sum(
        row["khoa_con_co_gia_tri"]
        for row in tq3_rows
    )

    tq4_valid = sum(
        row["so_dong_hop_le"]
        for row in tq4_rows
    )

    tq4_total = sum(
        row["so_dong"]
        for row in tq4_rows
    )

    results = [
        {
            "technical_kpi_id": "TQ-01",
            "technical_kpi_name": "Tỷ lệ thiếu dữ liệu",
            "ket_qua": (
                round(total_null / total_cells * 100, 4)
                if total_cells else None
            ),
            "don_vi": "%",
            "trang_thai": "Đã tính",
            "dien_giai": (
                f"{total_null:,}/{total_cells:,} ô "
                "ở các trường bắt buộc bị thiếu."
            )
        },
        {
            "technical_kpi_id": "TQ-02",
            "technical_kpi_name": "Số bản ghi trùng khóa",
            "ket_qua": tq2_total,
            "don_vi": "Dòng trùng dư",
            "trang_thai": "Đã tính",
            "dien_giai": (
                "Tổng số dòng trùng dư theo khóa/grain "
                "đã xác định. Khóa thiếu được báo cáo riêng."
            )
        },
        {
            "technical_kpi_id": "TQ-03",
            "technical_kpi_name": "Tỷ lệ toàn vẹn tham chiếu",
            "ket_qua": (
                round(tq3_valid / tq3_nonnull * 100, 4)
                if tq3_nonnull else None
            ),
            "don_vi": "%",
            "trang_thai": "Đã tính",
            "dien_giai": (
                f"{tq3_valid:,}/{tq3_nonnull:,} khóa con "
                "có giá trị liên kết được."
            )
        },
        {
            "technical_kpi_id": "TQ-04",
            "technical_kpi_name": "Tỷ lệ bản ghi hợp lệ",
            "ket_qua": (
                round(tq4_valid / tq4_total * 100, 4)
                if tq4_total else None
            ),
            "don_vi": "%",
            "trang_thai": "Đã tính theo luật tối thiểu công bố",
            "dien_giai": (
                f"{tq4_valid:,}/{tq4_total:,} dòng "
                "đạt luật kiểm tra tối thiểu."
            )
        },
        {
            "technical_kpi_id": "TQ-05",
            "technical_kpi_name": "Tính nhất quán khi chạy lại pipeline",
            "ket_qua": None,
            "don_vi": "PASS/FAIL",
            "trang_thai": "CHƯA ĐÁNH GIÁ",
            "dien_giai": (
                "Cần log của ít nhất hai lần chạy ETL "
                "với cùng dữ liệu và cấu hình."
            )
        }
    ]

    result_df = pd.DataFrame(results)

    result_df.to_csv(
        output_dir / "technical_kpi_results.csv",
        index=False,
        encoding="utf-8-sig"
    )

    return (
        audit,
        pd.DataFrame(validation_rows),
        result_df,
        pd.DataFrame(details)
    )

def build_executed_notebook(execute=False):
    """Tạo notebook chạy trực tiếp các hàm từ raw và lưu output thực thi."""
    notebook_path = ROOT / "notebooks" / "02_data_dictionary_kpi.ipynb"
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    cells = [
        nbformat.v4.new_markdown_cell(
            "# Task 2.2 – Data Dictionary và KPI\n"
            "Chạy lại từ dữ liệu raw; CSV kết quả được tạo tự động. "
            "Không chỉnh sửa raw. Định nghĩa và quy tắc được quản lý trong scripts/data_dictionary_kpi.py."
        ),
        nbformat.v4.new_code_cell(
            "from pathlib import Path\nimport importlib.util\nfrom IPython.display import display\n"
            "ROOT = next((p for p in [Path.cwd(), *Path.cwd().parents] "
            "if (p / 'scripts' / 'data_dictionary_kpi.py').is_file() "
            "and (p / 'data' / 'raw').is_dir()), None)\n"
            "if ROOT is None: raise FileNotFoundError('Mở notebook trong thư mục repo có data/raw.')\n"
            "spec = importlib.util.spec_from_file_location('dictionary_kpi', ROOT / 'scripts' / 'data_dictionary_kpi.py')\n"
            "module = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(module)\n"
            "dictionary = module.build_dictionary()\nmodule.write_kpis()\n"
            "audit, source_checks, technical_results, technical_detail = module.build_quality_results(dictionary)\n"
            "print('Đã tái tạo dictionary và kiểm tra từ 4 nguồn raw.')"
        ),
        nbformat.v4.new_markdown_cell("## Schema và quy tắc chuyển đổi"),
        nbformat.v4.new_code_cell(
            "print('Số trường:', len(dictionary))\n"
            "display(dictionary.groupby('source_name').size().rename('column_count').to_frame())\n"
            "display(dictionary[['source_name', 'column_name', 'business_meaning', 'proposed_transformation']])"
        ),
        nbformat.v4.new_markdown_cell("## Định nghĩa: 5 Business KPI, 2 chỉ tiêu hỗ trợ, 5 Technical KPI"),
        nbformat.v4.new_code_cell(
            "display(module.pd.DataFrame(module.BUSINESS_KPIS))\n"
            "display(module.pd.DataFrame(module.TECH_KPIS))"
        ),
        nbformat.v4.new_markdown_cell("## Bằng chứng từ raw và Technical KPI tối thiểu"),
        nbformat.v4.new_code_cell(
            "display(source_checks)\ndisplay(technical_results)\ndisplay(technical_detail)\n"
            "assert len(dictionary) == 103\n"
            "assert technical_results.loc[technical_results.technical_kpi_id == 'TQ-05', 'trang_thai'].iloc[0] == 'CHƯA ĐÁNH GIÁ'"
        ),
        nbformat.v4.new_markdown_cell(
            "## Giới hạn\nTQ-01 đến TQ-04 ở đây là kiểm tra raw theo luật tối thiểu công bố, "
            "chưa chứng minh chất lượng Gold. TQ-05 cần hai lần chạy ETL thực tế. "
            "Miền rating 1–5 là miền quan sát; cần xác nhận metadata nguồn khi chốt ETL. "
            "Các file outputs/task_2_2 được tạo lại khi chạy, không phải dữ liệu đầu vào."
        )
    ]
    notebook = nbformat.v4.new_notebook(cells=cells, metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}})
    if not execute:
        nbformat.write(notebook, notebook_path)
        return notebook_path
    from nbclient import NotebookClient
    client = NotebookClient(notebook, timeout=600, kernel_name="python3",
                            resources={"metadata": {"path": str(ROOT)}})
    executed = client.execute()
    # Tránh lưu đường dẫn của máy chạy trong metadata thời gian thực thi.
    for cell in executed.cells:
        cell.metadata.pop("execution", None)
    nbformat.write(executed, notebook_path)
    return notebook_path

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Tái tạo Dictionary/KPI từ raw, không cần MySQL.")
    parser.add_argument("--execute-notebook", action="store_true", help="Chạy notebook bằng Jupyter kernel và lưu output.")
    args = parser.parse_args()

    print("TASK 2.2 - DATA DICTIONARY & KPI")

    # 1. Xây dựng Data Dictionary
    dictionary = build_dictionary()

    # 2. Xuất định nghĩa Business KPI và Technical KPI
    write_kpis()

    # 3. Kiểm tra chất lượng dữ liệu và tính Technical KPI
    build_quality_results(dictionary)

    # 4. Tạo và chạy Notebook
    notebook_path = build_executed_notebook(execute=args.execute_notebook)

    print("\n========== KẾT QUẢ ==========")

    print(
        "[PASS] Data Dictionary:",
        len(dictionary),
        "trường"
    )

    print(
        "[PASS] Số nguồn dữ liệu:",
        len(SOURCES)
    )

    print(
        "[PASS] Business KPI:",
        len(BUSINESS_KPIS)
    )

    print(
        "[PASS] Technical KPI:",
        len(TECH_KPIS)
    )

    print(
        "[PASS] Đã tính kết quả TQ-01 đến TQ-04"
    )

    print(
        "[INFO] TQ-05: CHƯA ĐÁNH GIÁ"
    )

    print("Notebook:", notebook_path)

    print("Dữ liệu raw không bị chỉnh sửa.")


if __name__ == "__main__":
    main()
