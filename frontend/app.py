import streamlit as st
import requests
import base64
import io
from PIL import Image

# Set page config with modern title and icon
st.set_page_config(
    page_title="PDF Stamp Remover - Xóa Dấu Mộc PDF",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend service configuration
BACKEND_URL = "http://127.0.0.1:8000"

# Inject Custom CSS for premium styling, dark mode, fonts, gradients and animations
st.markdown("""
<style>
    /* Import modern typography */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Global Background and Style */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    
    /* Header Gradient styling */
    .main-title {
        font-size: 3rem !important;
        font-weight: 800;
        background: linear-gradient(90deg, #ff4b4b 0%, #ff8a00 50%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.2rem;
        padding-top: 1rem;
    }
    .subtitle {
        font-size: 1.2rem;
        font-weight: 300;
        text-align: center;
        color: #8b949e;
        margin-bottom: 2.5rem;
    }
    
    /* Sidebar styling styling */
    section[data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d;
    }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2 {
        color: #f0f6fc;
        font-weight: 600;
    }
    
    /* Containers / Cards */
    div.stAlert {
        border-radius: 12px;
        border: 1px solid #30363d;
        background-color: #161b22;
    }
    
    /* Styled preview headers */
    .preview-header {
        font-weight: 600;
        font-size: 1.1rem;
        text-align: center;
        padding: 8px;
        background: #1f2937;
        border-radius: 8px 8px 0 0;
        color: #f0f6fc;
        border: 1px solid #374151;
        border-bottom: none;
    }
    .preview-box {
        border: 1px solid #374151;
        border-radius: 0 0 8px 8px;
        padding: 8px;
        background: #111827;
        text-align: center;
    }
    
    /* Premium Streamlit button customization */
    div.stButton > button {
        background: linear-gradient(135deg, #ff4b4b 0%, #d83b3b 100%) !important;
        color: white !important;
        border: none !important;
        padding: 0.75rem 2.5rem !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        border-radius: 30px !important;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4) !important;
        transition: all 0.3s ease !important;
        width: 100%;
        margin-top: 1rem;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 75, 75, 0.6) !important;
        background: linear-gradient(135deg, #ff6b6b 0%, #ff4b4b 100%) !important;
    }
    div.stButton > button:active {
        transform: translateY(0px) !important;
    }
    
    /* Download Button styling */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: white !important;
        border: none !important;
        padding: 0.75rem 2.5rem !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        border-radius: 30px !important;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4) !important;
        transition: all 0.3s ease !important;
        width: 100%;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.6) !important;
        background: linear-gradient(135deg, #34d399 0%, #10b981 100%) !important;
    }
    
    /* Sliders styling */
    span[data-baseweb="slider-thumb"] {
        background-color: #ff4b4b !important;
    }
    div[data-baseweb="slider-track"] > div {
        background-color: #ff4b4b !important;
    }
</style>
""", unsafe_allow_html=True)

# Main App Title
st.markdown('<div class="main-title">📄 PDF Stamp Remover</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Tách và xóa dấu mộc (đỏ, xanh, tím...) ra khỏi file PDF nhanh chóng sử dụng Computer Vision</div>', unsafe_allow_html=True)

# Sidebar layout
st.sidebar.markdown("## ⚙️ Cấu hình bộ lọc")

# File uploader
uploaded_file = st.file_uploader("Kéo thả hoặc chọn file PDF cần xử lý tại đây", type=["pdf"])

# Parameters sidebar
preset = st.sidebar.selectbox(
    "Màu sắc dấu mộc cần xóa:",
    options=["red", "blue", "purple", "custom"],
    format_func=lambda x: {
        "red": "🔴 Dấu mộc Đỏ / Cam",
        "blue": "🔵 Dấu mộc Xanh dương",
        "purple": "🟣 Dấu mộc Tím",
        "custom": "🛠️ Tùy chỉnh (HSV)"
    }.get(x, x)
)

# Custom color sliders if "custom" is selected
h_min_1, h_max_1 = 0, 12
h_min_2, h_max_2 = 168, 180
sat_min, sat_max = 40, 255
val_min, val_max = 40, 255

if preset == "custom":
    st.sidebar.markdown("### 🎨 Dải màu HSV")
    
    st.sidebar.markdown("**Dải Hue 1 (Màu đỏ bắt đầu hoặc màu khác)**")
    h_min_1 = st.sidebar.slider("Min Hue 1", 0, 180, 0)
    h_max_1 = st.sidebar.slider("Max Hue 1", 0, 180, 12)
    
    st.sidebar.markdown("**Dải Hue 2 (Màu đỏ kết thúc - thường dùng cho sắc đỏ)**")
    h_min_2 = st.sidebar.slider("Min Hue 2", 0, 180, 168)
    h_max_2 = st.sidebar.slider("Max Hue 2", 0, 180, 180)
    
    st.sidebar.markdown("**Độ bão hòa (Saturation) & Độ sáng (Value)**")
    sat_min = st.sidebar.slider("Min Saturation", 0, 255, 40)
    sat_max = st.sidebar.slider("Max Saturation", 0, 255, 255)
    val_min = st.sidebar.slider("Min Value (Brightness)", 0, 255, 40)
    val_max = st.sidebar.slider("Max Value (Brightness)", 0, 255, 255)

st.sidebar.markdown("### 🎚️ Tham số xử lý nâng cao")

dilation = st.sidebar.slider(
    "Độ rộng nét xóa (Dilation):",
    min_value=0,
    max_value=5,
    value=1,
    help="Tăng giá trị này để xóa sạch các viền mờ xung quanh dấu mộc."
)

preview_dpi = st.sidebar.slider(
    "Độ phân giải hiển thị (DPI):",
    min_value=72,
    max_value=300,
    value=150,
    step=10,
    help="DPI cao hơn sẽ hiển thị ảnh nét hơn nhưng xử lý lâu hơn."
)

st.sidebar.markdown("### 🧹 Xóa thêm nội dung")

remove_sig = st.sidebar.checkbox(
    "✍️ Xóa chữ ký (Signature)",
    value=False,
    help="Tự động tìm và xóa vùng chữ ký trên tài liệu."
)

remove_billno = st.sidebar.checkbox(
    "🔢 Xóa dòng Bill No",
    value=False,
    help="Tự động tìm và xóa dòng 'Bill No:' trên tài liệu."
)

if uploaded_file is not None:
    # Read PDF file bytes
    file_bytes = uploaded_file.read()
    
    # Store page index in session state if not present
    if 'page_num' not in st.session_state:
        st.session_state.page_num = 0
        
    # We will call the preview API to get total pages and preview images
    with st.spinner("Đang chuẩn bị bản xem trước..."):
        try:
            files = {"file": (uploaded_file.name, file_bytes, "application/pdf")}
            data = {
                "page_num": st.session_state.page_num,
                "preset": preset,
                "hue_min_1": h_min_1,
                "hue_max_1": h_max_1,
                "hue_min_2": h_min_2,
                "hue_max_2": h_max_2,
                "sat_min": sat_min,
                "sat_max": sat_max,
                "val_min": val_min,
                "val_max": val_max,
                "dilation": dilation,
                "dpi": preview_dpi,
                "remove_sig": 1 if remove_sig else 0,
                "remove_billno": 1 if remove_billno else 0
            }
            
            response = requests.post(f"{BACKEND_URL}/preview/", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                total_pages = result["total_pages"]
                
                # Render page navigation controls
                col_nav_1, col_nav_2, col_nav_3 = st.columns([1, 2, 1])
                with col_nav_2:
                    st.write("") # Spacer
                    if total_pages > 1:
                        st.markdown(f"<div style='text-align: center; font-weight: 600; margin-bottom: -10px;'>Trang {st.session_state.page_num + 1} / {total_pages}</div>", unsafe_allow_html=True)
                        selected_page = st.slider(
                            "Chọn trang xem trước:",
                            min_value=1,
                            max_value=total_pages,
                            value=st.session_state.page_num + 1
                        )
                        st.session_state.page_num = selected_page - 1
                    else:
                        st.session_state.page_num = 0
                        st.markdown("<div style='text-align: center; font-weight: 600;'>Trang 1 / 1</div>", unsafe_allow_html=True)
                
                # Side-by-side previews
                st.markdown("### 🔍 So sánh bản xem trước")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown('<div class="preview-header">Original (Trang gốc)</div>', unsafe_allow_html=True)
                    orig_img = Image.open(io.BytesIO(base64.b64decode(result["original"])))
                    st.image(orig_img, use_column_width=True)
                    
                with col2:
                    st.markdown('<div class="preview-header">Cleaned (Đã xóa dấu mộc)</div>', unsafe_allow_html=True)
                    clean_img = Image.open(io.BytesIO(base64.b64decode(result["cleaned"])))
                    st.image(clean_img, use_column_width=True)
                    
                # Full Document Processing Button
                st.markdown("---")
                st.markdown("### ⚡ Xử lý toàn bộ tài liệu")
                st.write("Nếu bản xem trước đã chính xác, hãy click nút dưới đây để xử lý toàn bộ các trang và tải file PDF kết quả.")
                
                col_btn_1, col_btn_2, col_btn_3 = st.columns([1, 2, 1])
                with col_btn_2:
                    if st.button("🚀 Bắt đầu xóa mộc toàn bộ PDF"):
                        with st.spinner("Đang xử lý toàn bộ tài liệu... Vui lòng đợi trong giây lát."):
                            # Reset file pointer and re-upload
                            files_all = {"file": (uploaded_file.name, file_bytes, "application/pdf")}
                            response_all = requests.post(f"{BACKEND_URL}/process/", files=files_all, data=data)
                            
                            if response_all.status_code == 200:
                                st.success("Xử lý thành công! Nhấp vào nút phía dưới để tải file về.")
                                st.download_button(
                                    label="📥 Tải PDF Đã Xóa Mộc",
                                    data=response_all.content,
                                    file_name=f"cleaned_{uploaded_file.name}",
                                    mime="application/pdf"
                                )
                            else:
                                st.error(f"Lỗi khi xử lý toàn bộ: {response_all.text}")
            else:
                st.error(f"Không thể tải bản xem trước từ Backend: {response.text}")
                
        except Exception as e:
            st.error(f"Kết nối tới Backend thất bại. Hãy chắc chắn FastAPI đang chạy. Chi tiết lỗi: {e}")
else:
    # Interactive instructions card
    st.info("💡 Vui lòng tải một file PDF lên ở khung phía trên để bắt đầu sử dụng ứng dụng.")
    
    # Showcase features in standard markdown cards
    st.markdown("""
    ### 🌟 Các chức năng nổi bật của ứng dụng:
    1. **Xử lý cực nhanh**: Chuyển đổi và xử lý trực tiếp bằng thư viện hiệu năng cao `PyMuPDF` kết hợp `OpenCV` tối ưu.
    2. **Đa dạng màu sắc**: Hỗ trợ xóa mộc đỏ (hóa đơn, hợp đồng), mộc xanh, mộc tím, hoặc tự điều chỉnh bất kỳ dải màu nào bằng chế độ Custom.
    3. **Xem trước thời gian thực (Real-time Preview)**: Cho phép điều chỉnh dải màu, độ rộng nét xóa và xem trước kết quả trực tiếp trước khi xuất file.
    4. **Không cần cài đặt Poppler**: Tối ưu hóa cho môi trường Windows, chạy trực tiếp không phụ thuộc các gói nhị phân phức tạp.
    """)
