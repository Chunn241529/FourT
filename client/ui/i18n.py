"""
FourT Suite - Internationalization (i18n) Module
Provides multi-language support for the desktop client
"""

import json
import os
from typing import Dict, Optional
from pathlib import Path

# Default language
_current_language = "vi"

# Translations dictionary
_translations: Dict[str, Dict[str, str]] = {
    "vi": {
        # Menu Launcher
        "trial_remaining": "TRIAL: {minutes} phút còn lại",
        "auto_play_midi": "Auto play midi",
        "auto_play_midi_expired": "Auto play midi (Hết hạn)",
        "quest_video_helper": "Quest video helper",
        "quest_video_helper_plus": "Quest video helper (PLUS)",
        "ping_optimizer": "Ping optimizer",
        "ping_optimizer_pro": "Ping optimizer (PRO)",
        "macro_recorder": "Macro recorder",
        "macro_recorder_pro": "Macro recorder (PRO)",
        "macro_combo": "Macro combo",
        "macro_combo_pro": "Macro combo (PRO)",
        "screen_translator": "Dịch màn hình",
        "upgrade_premium": "Nâng cấp premium",
        "sync_server": "Đồng bộ server",
        "exit": "Thoát",
        # Feature Restrictions
        "feature_of_package": "{feature_name} là tính năng của gói {package} trở lên.",
        "want_to_upgrade": "Bạn có muốn nâng cấp ngay không?",
        "feature_title": "Tính năng {feature_name}",
        # Macro Recorder
        "macro_helps": "Tính năng này giúp:\n• Ghi lại thao tác\n• Phát lại tự động",
        # WWM Combo
        "wwm_helps": "Tính năng này giúp:\n• Tạo combo skills\n• Auto trigger khi combat",
        # MIDI
        "trial_ended": "Thời gian dùng thử đã kết thúc.",
        # Quest Helper
        "quest_helps": "Tính năng này giúp:\n• OCR đọc tên quest từ màn hình\n• Tự động tìm video hướng dẫn\n• Hiển thị video ngay cạnh game",
        # Ping Optimizer
        "ping_helps": "Tính năng này giúp:\n• Tối ưu TCP/IP settings\n• Đổi DNS nhanh nhất\n• Flush network cache",
        # Screen Translator
        "screen_translator": "Dịch Màn Hình",
        "screen_translator_plus": "Dịch Màn Hình 🔒",
        "screen_translator_helps": "Tính năng này giúp:\n• OCR đọc text từ màn hình\n• Dịch realtime sang tiếng Việt\n• Hiển thị overlay không che game",
        # Screen Translator Window
        "st_title": "Dịch Màn Hình",
        "st_subtitle": "Chọn vùng màn hình để dịch văn bản từ game",
        "st_language": "Ngôn ngữ",
        "st_capture_once": "📷  Chụp & Dịch một lần",
        "st_realtime": "🔄  Dịch Real-time",
        "st_realtime_desc": "Liên tục dịch vùng đã chọn",
        "st_realtime_running": "🔴 Đang dịch...",
        "st_stop_realtime": "⏹ Dừng Real-time",
        "st_settings": "Cài đặt",
        "st_ocr_engine": "OCR Engine:",
        "st_ocr_ready": "{engine} sẵn sàng",
        "st_ocr_need_setup": "Cần cài đặt OCR",
        "st_skip_character": "Bỏ tên nhân vật (game dialogue)",
        "st_interval": "Realtime interval:",
        "st_select_region": "Tô vùng chứa text cần dịch",
        "st_select_realtime": "Tô vùng để dịch liên tục",
        "st_no_text": "Không nhận diện được text",
        "st_text_unclear": "Text không rõ ràng, vui lòng chọn vùng khác",
        "st_stopped": "⏹ Đã dừng dịch realtime",
        "st_translate": "Dịch",
        # Sync
        "sync_completed": "Đồng bộ hoàn tất!",
        "downloading_update": "Đang tải cập nhật...",
        "download_complete": "Tải xong!",
        # Exit Confirmation
        "confirm_exit": "Xác nhận thoát",
        "exit_message": "Bạn có chắc chắn muốn thoát ứng dụng?",
        "btn_cancel": "Hủy",
        "btn_exit": "Thoát",
        # Upgrade Window
        "upgrade_title": "Nâng cấp FourT Suite",
        "loading_packages": "⏳ Đang tải thông tin gói...",
        "choose_package": "Chọn gói phù hợp với bạn",
        "unlock_potential": "Mở khóa toàn bộ tiềm năng của FourT Suite",
        "have_license_key": "Đã có License Key?",
        "activate": "Kích hoạt",
        "select_package": "Chọn gói này",
        "1_month": "1 tháng",
        "1_year": "1 năm",
        "1_week": "1 tuần",
        "days": "{days} ngày",
        "recommended": "RECOMMENDED",
        "or": "hoặc",
        "missing_license": "Thiếu License Key",
        "enter_license": "Vui lòng nhập license key.",
        "success": "Thành công",
        "license_activated": "License đã được kích hoạt!\nGói: {package}",
        "error": "Lỗi",
        "license_invalid": "License key không hợp lệ hoặc đã được sử dụng trên thiết bị khác.",
        "upgrade_success": "Cảm ơn bạn đã nâng cấp! Vui lòng khởi động lại ứng dụng.",
        # MIDI Player
        "midi_player": "MIDI Auto Player",
        "add": "Thêm",
        "from_library": "📂  Từ thư viện...",
        "browse_file": "📁  Duyệt file...",
        "mp3_to_midi": "🎵  MP3 → MIDI...",
        "choose_song": "📂 Chọn bài hát",
        "add_btn": "Thêm",
        "cancel": "Hủy",
        "playlist_empty": "\n🎵\n\nPlaylist trống\n\nClick '+ Thêm' để thêm bài",
        "songs": "{count} bài",
        "songs_with_name": "{count} bài • {name}",
        "ready": "✨ Sẵn sàng",
        "stopped": "⏸️ Đã dừng",
        "stopped_all": "⏹ Đã dừng tất cả",
        "processing": "⏳ Đang xử lý...",
        "playing": "🎵 Đang phát...",
        "completed": "✅ Hoàn thành",
        "preview": "✅ Xem trước",
        "countdown": "Chuyển sang game trong... {count} giây",
        "speed_title": "Tốc độ phát",
        "speed_prompt": "Nhập tốc độ ({min:.1f} - {max:.1f}):",
        "expired": "Hết hạn",
        "upgrade_to_continue": "Vui lòng nâng cấp để tiếp tục.",
        "file_not_exist": "File không tồn tại!",
        "midi_empty": "File MIDI trống!",
        "midi_error": "Lỗi đọc MIDI: {error}",
        "select_to_preview": "Chọn một bài để xem trước!",
        "converting": "⏳ Đang chuyển đổi...",
        "server_offline": "❌ Server offline",
        "created": "✅ Đã tạo: {filename}",
        "convert_error": "❌ Lỗi: {error}",
        "mp3_upgrade": "Tính năng MP3→MIDI từ gói Pro.",
        "save_playlist": "Lưu Playlist",
        "enter_name": "Nhập tên:",
        "saved": "Đã lưu '{name}'",
        "cannot_save": "Không thể lưu",
        "open_playlist": "Mở Playlist",
        "no_playlist": "Chưa có playlist",
        "open": "Mở",
        "confirm": "Xác nhận",
        "delete_all": "Xóa tất cả?",
        "playlist_empty_info": "Playlist trống!",
        "opening_community": "🌐 Đang mở Community...",
        # Ping Optimizer
        "excellent": "Xuất sắc",
        "good": "Tốt",
        "average": "Trung bình",
        "poor": "Kém",
        "very_poor": "Rất kém",
        "measuring_ping": "Đang đo ping...",
        "optimizing_tcp": "Đang tối ưu TCP/IP...",
        "optimize_success": "✅ Tối ưu thành công!",
        "need_admin": "⚠️ Cần chạy với quyền Admin",
        "flushing_network": "Đang flush network...",
        "flush_success": "✅ Flush thành công!",
        "some_need_admin": "⚠️ Một số lệnh cần Admin",
        "benchmarking_dns": "Đang benchmark DNS...",
        "testing_dns": "Testing {name}: {latency:.0f}ms",
        "fastest_dns": "🏆 DNS nhanh nhất: {name} ({latency:.0f}ms)",
        "cannot_benchmark": "Không thể benchmark DNS",
        "changing_dns": "Đang đổi DNS...",
        "dns_changed": "✅ Đã đổi DNS!",
        "optimize": "Optimize",
        "flush_dns": "Flush DNS",
        "best_dns": "Best DNS",
        "dns_server": "DNS Server:",
        "apply": "Apply",
        # Bug Report
        "bug_report": "Báo cáo lỗi",
        "bug_title": "Tiêu đề *",
        "bug_description": "Mô tả lỗi *",
        "bug_placeholder": "Mô tả chi tiết lỗi bạn gặp phải:\n- Lỗi xảy ra khi nào?\n- Các bước tái hiện lỗi?\n- Có thông báo lỗi gì không?",
        "attach_file": "Đính kèm hình ảnh/video (tối đa 100MB)",
        "no_file": "Chưa chọn file",
        "choose_file": "📁 Chọn file",
        "send_report": "📤 Gửi báo cáo",
        "file_too_large": "File quá lớn",
        "file_size_limit": "File có dung lượng {size:.1f}MB, vượt quá giới hạn {max}MB.\n\nVui lòng chọn file nhỏ hơn.",
        "format_not_supported": "Định dạng không hỗ trợ",
        "supported_formats": "Chỉ hỗ trợ các định dạng:\n• Hình ảnh: PNG, JPG, GIF, BMP, WebP\n• Video: MP4, WebM, MOV, AVI, MKV",
        "enter_title": "⚠ Vui lòng nhập tiêu đề",
        "enter_description": "⚠ Vui lòng mô tả lỗi",
        "sending": "Đang gửi...",
        "sending_report": "📤 Đang gửi báo cáo...",
        "thank_you": "Cảm ơn bạn!",
        "email_opened": "Đã mở ứng dụng email.\nVui lòng gửi email để hoàn tất báo cáo.",
        "report_sent": "Báo cáo lỗi của bạn đã được gửi thành công.\nChúng tôi sẽ xem xét và phản hồi sớm nhất!",
        "close": "Đóng",
        # Splash Screen
        "connecting": "Connecting...",
        "updating_server": "Updating server URL...",
        "clearing_cache": "Clearing cache...",
        "optimizing_memory": "Optimizing memory...",
        "verifying_license": "Verifying license...",
        "syncing_skills": "Syncing skills...",
        "loading_modules": "Loading modules...",
        "loading_icons": "Loading skill icons...",
        "loading_templates": "Loading templates...",
        "syncing_midi": "Syncing MIDI library...",
        "checking_updates": "Checking updates...",
        "downloading_update_splash": "Downloading update...",
        "ready_splash": "Ready!",
        "server_connected": "Server connected!",
        "server_url_updated": "Server URL updated",
        "update_available": "Update available!",
        "no_updates": "No updates",
        "offline_mode": "Offline mode",
        "license_verified": "License verified",
        "sync_complete": "Sync complete",
        # Common
        "yes": "Có",
        "no": "Không",
        "ok": "OK",
        "save": "Lưu",
        "loading": "Đang tải...",
        "warning": "Cảnh báo",
        "info": "Thông tin",
        "delete": "Xóa",
        # Quest Video Helper
        "quest_quick_guide": "💡 Cách sử dụng nhanh:",
        "quest_step_1": '1. Nhấn "Bắt đầu chọn vùng" (hoặc phím tắt)',
        "quest_step_2": "2. Kéo chuột chọn vùng chứa tên quest",
        "quest_step_3": "3. Video hướng dẫn sẽ tự động mở",
        "start_select_region": "🎯  Bắt đầu chọn vùng",
        "hotkey_label": "Phím tắt: {hotkey}",
        "settings": "⚙️  Cài đặt",
        "hotkey": "Phím tắt:",
        "search_prefix": "Tiền tố tìm kiếm:",
        "search_suffix": "Hậu tố tìm kiếm:",
        "language": "Ngôn ngữ:",
        "video_size": "Kích thước video:",
        "auto_play_video": "Tự động phát video",
        "save_settings": "💾  Lưu cài đặt",
        "settings_saved": "Đã lưu cài đặt!",
        "cannot_save_settings": "Không thể lưu cài đặt",
        "video_size_number": "Kích thước video phải là số",
        "press_key": "Nhấn phím...",
        "ocr_status": "Trạng thái: {status}",
        "ocr_ready": "Sẵn sàng",
        "ocr_setup": "Cài đặt",
        "select_quest_region": "Kéo chuột để chọn vùng chứa tên quest",
        "no_text_found": "Không tìm thấy text",
        "cannot_read_text": "Không thể đọc text từ vùng đã chọn.\nHãy thử chọn lại vùng khác.",
        "preparing_video": "🔄 Đang chuẩn bị video...",
        "please_wait": "Vui lòng đợi...",
        # Macro Recorder
        "macro_library": "📚 Library",
        "no_macros": "Chưa có macro nào",
        "confirm_delete": "Xác nhận",
        "delete_macro": "Xóa macro '{name}'?",
        "cannot_delete_macro": "Không thể xóa macro: {error}",
        "timeline_reorder": "Timeline (Drag to Reorder)",
        "clear_all": "🗑 Clear All",
        "add_delay": "⏳ + Delay",
        "trigger": "Trigger:",
        "save_to_library": "💾 Save to Library",
        "active_background": "Active Background Macros",
        "add_current_active": "+ Add Current to Active",
        "macro_ready": "Ready",
        "recording": "🔴 Recording...",
        "macro_name": "Macro Name",
        "enter_macro_name": "Enter macro name:",
        "macro_saved": "Macro saved!",
        "macro_save_error": "Cannot save macro",
        # WWM Combo
        "wwm_warning": "Đây không phải hack/cheat - không inject vào thư mục game, đây là macro hỗ trợ nối combo.\nXin hãy lưu ý và sử dụng có trách nhiệm, không nên lạm dụng, không nên spam skill.",
        "skills": "🎮 Skills",
        "weapon": "Vũ khí:",
        "templates": "📋 Templates",
        "common_skills": "⭐ Chung",
        "combo_timeline": "Combo Timeline:",
        "guide_title": "📖 Hướng dẫn",
        "drag_tip": "Kéo thả skill từ bên trái vào timeline.\nThêm delay bằng cách nhấn button '+ Delay'.\nDouble-click delay để chỉnh.\nCó thể di chuyển để sắp xếp lại.",
        "activate_instruction": "Set button trigger sau đó nhấn 'Add to Active' để kích hoạt macro.",
        "test": "▶ Test",
        "add_to_active": "+ Add to Active",
        "active_combos": "🔥 Active Combos",
        "load_combo": "📂 Load Combo",
        "empty_combo": "Create a combo first!",
        "save_template": "Save Template",
        "enter_template_name": "Enter template name:",
        "template_exists": "Template '{name}' exists. Overwrite?",
        "template_saved": "Template '{name}' saved!",
        "template_save_error": "Failed to save template",
        "delete_template": "Delete template '{name}'?",
        "template_deleted": "Template '{name}' deleted",
        "added_template": "Added template '{name}' to timeline",
    },
    "en": {
        # Menu Launcher
        "trial_remaining": "TRIAL: {minutes} min remaining",
        "auto_play_midi": "Auto play midi",
        "auto_play_midi_expired": "Auto play midi (Expired)",
        "quest_video_helper": "Quest video helper",
        "quest_video_helper_plus": "Quest video helper (PLUS)",
        "ping_optimizer": "Ping optimizer",
        "ping_optimizer_pro": "Ping optimizer (PRO)",
        "macro_recorder": "Macro recorder",
        "macro_recorder_pro": "Macro recorder (PRO)",
        "macro_combo": "Macro combo",
        "macro_combo_pro": "Macro combo (PRO)",
        "screen_translator": "Screen translator",
        "upgrade_premium": "Upgrade premium",
        "sync_server": "Sync server",
        "exit": "Exit",
        # Feature Restrictions
        "feature_of_package": "{feature_name} is a feature of {package} package or higher.",
        "want_to_upgrade": "Do you want to upgrade now?",
        "feature_title": "{feature_name} Feature",
        # Macro Recorder
        "macro_helps": "This feature helps:\n• Record actions\n• Auto playback",
        # WWM Combo
        "wwm_helps": "This feature helps:\n• Create skill combos\n• Auto trigger in combat",
        # MIDI
        "trial_ended": "Trial period has ended.",
        # Quest Helper
        "quest_helps": "This feature helps:\n• OCR read quest name from screen\n• Auto search tutorial video\n• Display video next to game",
        # Ping Optimizer
        "ping_helps": "This feature helps:\n• Optimize TCP/IP settings\n• Switch to fastest DNS\n• Flush network cache",
        # Screen Translator
        "screen_translator": "Screen Translator",
        "screen_translator_plus": "Screen Translator 🔒",
        "screen_translator_helps": "This feature helps:\n• OCR read text from screen\n• Real-time translate to Vietnamese\n• Display overlay without blocking game",
        # Screen Translator Window
        "st_title": "Screen Translator",
        "st_subtitle": "Select screen region to translate game text",
        "st_language": "Language",
        "st_capture_once": "📷  Capture & Translate once",
        "st_realtime": "🔄  Real-time translate",
        "st_realtime_desc": "Continuously translate selected region",
        "st_realtime_running": "🔴 Translating...",
        "st_stop_realtime": "⏹ Stop Real-time",
        "st_settings": "Settings",
        "st_ocr_engine": "OCR Engine:",
        "st_ocr_ready": "{engine} ready",
        "st_ocr_need_setup": "OCR setup required",
        "st_skip_character": "Skip character name (game dialogue)",
        "st_interval": "Realtime interval:",
        "st_select_region": "Draw region containing text to translate",
        "st_select_realtime": "Draw region for continuous translation",
        "st_no_text": "No text detected",
        "st_text_unclear": "Text unclear, please select another region",
        "st_stopped": "⏹ Stopped realtime translation",
        "st_translate": "Translate",
        # Sync
        "sync_completed": "Sync completed!",
        "downloading_update": "Downloading update...",
        "download_complete": "Download complete!",
        # Exit Confirmation
        "confirm_exit": "Confirm Exit",
        "exit_message": "Are you sure you want to exit the application?",
        "btn_cancel": "Cancel",
        "btn_exit": "Exit",
        # Upgrade Window
        "upgrade_title": "Upgrade FourT Suite",
        "loading_packages": "⏳ Loading package info...",
        "choose_package": "Choose the package that suits you",
        "unlock_potential": "Unlock the full potential of FourT Suite",
        "have_license_key": "Already have a License Key?",
        "activate": "Activate",
        "select_package": "Select this package",
        "1_month": "1 month",
        "1_year": "1 year",
        "1_week": "1 week",
        "days": "{days} days",
        "recommended": "RECOMMENDED",
        "or": "or",
        "missing_license": "Missing License Key",
        "enter_license": "Please enter your license key.",
        "success": "Success",
        "license_activated": "License activated!\nPackage: {package}",
        "error": "Error",
        "license_invalid": "License key is invalid or already used on another device.",
        "upgrade_success": "Thank you for upgrading! Please restart the application.",
        # MIDI Player
        "midi_player": "MIDI Auto Player",
        "add": "Add",
        "from_library": "📂  From library...",
        "browse_file": "📁  Browse file...",
        "mp3_to_midi": "🎵  MP3 → MIDI...",
        "choose_song": "📂 Choose song",
        "add_btn": "Add",
        "cancel": "Cancel",
        "playlist_empty": "\n🎵\n\nPlaylist empty\n\nClick '+ Add' to add songs",
        "songs": "{count} songs",
        "songs_with_name": "{count} songs • {name}",
        "ready": "✨ Ready",
        "stopped": "⏸️ Stopped",
        "stopped_all": "⏹ Stopped all",
        "processing": "⏳ Processing...",
        "playing": "🎵 Playing...",
        "completed": "✅ Completed",
        "preview": "✅ Preview",
        "countdown": "Switch to game in... {count} seconds",
        "speed_title": "Playback speed",
        "speed_prompt": "Enter speed ({min:.1f} - {max:.1f}):",
        "expired": "Expired",
        "upgrade_to_continue": "Please upgrade to continue.",
        "file_not_exist": "File does not exist!",
        "midi_empty": "MIDI file is empty!",
        "midi_error": "MIDI read error: {error}",
        "select_to_preview": "Select a song to preview!",
        "converting": "⏳ Converting...",
        "server_offline": "❌ Server offline",
        "created": "✅ Created: {filename}",
        "convert_error": "❌ Error: {error}",
        "mp3_upgrade": "MP3→MIDI feature from Pro package.",
        "save_playlist": "Save Playlist",
        "enter_name": "Enter name:",
        "saved": "Saved '{name}'",
        "cannot_save": "Cannot save",
        "open_playlist": "Open Playlist",
        "no_playlist": "No playlists yet",
        "open": "Open",
        "confirm": "Confirm",
        "delete_all": "Delete all?",
        "playlist_empty_info": "Playlist is empty!",
        "opening_community": "🌐 Opening Community...",
        # Ping Optimizer
        "excellent": "Excellent",
        "good": "Good",
        "average": "Average",
        "poor": "Poor",
        "very_poor": "Very Poor",
        "measuring_ping": "Measuring ping...",
        "optimizing_tcp": "Optimizing TCP/IP...",
        "optimize_success": "✅ Optimization successful!",
        "need_admin": "⚠️ Requires Admin rights",
        "flushing_network": "Flushing network...",
        "flush_success": "✅ Flush successful!",
        "some_need_admin": "⚠️ Some commands require Admin",
        "benchmarking_dns": "Benchmarking DNS...",
        "testing_dns": "Testing {name}: {latency:.0f}ms",
        "fastest_dns": "🏆 Fastest DNS: {name} ({latency:.0f}ms)",
        "cannot_benchmark": "Cannot benchmark DNS",
        "changing_dns": "Changing DNS...",
        "dns_changed": "✅ DNS changed!",
        "optimize": "Optimize",
        "flush_dns": "Flush DNS",
        "best_dns": "Best DNS",
        "dns_server": "DNS Server:",
        "apply": "Apply",
        # Bug Report
        "bug_report": "Bug Report",
        "bug_title": "Title *",
        "bug_description": "Description *",
        "bug_placeholder": "Describe the bug in detail:\n- When did it happen?\n- Steps to reproduce?\n- Any error messages?",
        "attach_file": "Attach image/video (max 100MB)",
        "no_file": "No file selected",
        "choose_file": "📁 Choose file",
        "send_report": "📤 Send report",
        "file_too_large": "File too large",
        "file_size_limit": "File size is {size:.1f}MB, exceeds limit of {max}MB.\n\nPlease choose a smaller file.",
        "format_not_supported": "Format not supported",
        "supported_formats": "Supported formats:\n• Images: PNG, JPG, GIF, BMP, WebP\n• Videos: MP4, WebM, MOV, AVI, MKV",
        "enter_title": "⚠ Please enter a title",
        "enter_description": "⚠ Please describe the bug",
        "sending": "Sending...",
        "sending_report": "📤 Sending report...",
        "thank_you": "Thank you!",
        "email_opened": "Email app opened.\nPlease send the email to complete the report.",
        "report_sent": "Your bug report has been sent successfully.\nWe will review and respond as soon as possible!",
        "close": "Close",
        # Splash Screen
        "connecting": "Connecting...",
        "updating_server": "Updating server URL...",
        "clearing_cache": "Clearing cache...",
        "optimizing_memory": "Optimizing memory...",
        "verifying_license": "Verifying license...",
        "syncing_skills": "Syncing skills...",
        "loading_modules": "Loading modules...",
        "loading_icons": "Loading skill icons...",
        "loading_templates": "Loading templates...",
        "syncing_midi": "Syncing MIDI library...",
        "checking_updates": "Checking updates...",
        "downloading_update_splash": "Downloading update...",
        "ready_splash": "Ready!",
        "server_connected": "Server connected!",
        "server_url_updated": "Server URL updated",
        "update_available": "Update available!",
        "no_updates": "No updates",
        "offline_mode": "Offline mode",
        "license_verified": "License verified",
        "sync_complete": "Sync complete",
        # Common
        "yes": "Yes",
        "no": "No",
        "ok": "OK",
        "save": "Save",
        "loading": "Loading...",
        "warning": "Warning",
        "info": "Info",
        "delete": "Delete",
        # Quest Video Helper
        "quest_quick_guide": "💡 Quick guide:",
        "quest_step_1": '1. Click "Start select region" (or hotkey)',
        "quest_step_2": "2. Drag to select area containing quest name",
        "quest_step_3": "3. Tutorial video will open automatically",
        "start_select_region": "🎯  Start select region",
        "hotkey_label": "Hotkey: {hotkey}",
        "settings": "⚙️  Settings",
        "hotkey": "Hotkey:",
        "search_prefix": "Search prefix:",
        "search_suffix": "Search suffix:",
        "language": "Language:",
        "video_size": "Video size:",
        "auto_play_video": "Auto play video",
        "save_settings": "💾  Save settings",
        "settings_saved": "Settings saved!",
        "cannot_save_settings": "Cannot save settings",
        "video_size_number": "Video size must be a number",
        "press_key": "Press key...",
        "ocr_status": "Status: {status}",
        "ocr_ready": "Ready",
        "ocr_setup": "Setup",
        "select_quest_region": "Drag to select area containing quest name",
        "no_text_found": "No text found",
        "cannot_read_text": "Cannot read text from selected area.\nTry selecting a different area.",
        "preparing_video": "🔄 Preparing video...",
        "please_wait": "Please wait...",
        # Macro Recorder
        "macro_library": "📚 Library",
        "no_macros": "No macros yet",
        "confirm_delete": "Confirm",
        "delete_macro": "Delete macro '{name}'?",
        "cannot_delete_macro": "Cannot delete macro: {error}",
        "timeline_reorder": "Timeline (Drag to Reorder)",
        "clear_all": "🗑 Clear All",
        "add_delay": "⏳ + Delay",
        "trigger": "Trigger:",
        "save_to_library": "💾 Save to Library",
        "active_background": "Active Background Macros",
        "add_current_active": "+ Add Current to Active",
        "macro_ready": "Ready",
        "recording": "🔴 Recording...",
        "macro_name": "Macro Name",
        "enter_macro_name": "Enter macro name:",
        "macro_saved": "Macro saved!",
        "macro_save_error": "Cannot save macro",
        # WWM Combo
        "wwm_warning": "This is not a hack/cheat - it doesn't inject into game files, it's a macro to chain combos.\nPlease use responsibly, avoid spamming skills.",
        "skills": "🎮 Skills",
        "weapon": "Weapon:",
        "templates": "📋 Templates",
        "common_skills": "⭐ Common",
        "combo_timeline": "Combo Timeline:",
        "guide_title": "📖 Guide",
        "activate_instruction": "Set trigger button then click 'Add to Active' to activate macro.",
        "drag_tip": "Drag skills from left to timeline.\nAdd delay using '+ Delay' button.\nDouble-click delay to edit.\nDrag to reorder.",
        "test": "▶ Test",
        "add_to_active": "+ Add to Active",
        "active_combos": "🔥 Active Combos",
        "load_combo": "📂 Load Combo",
        "empty_combo": "Create a combo first!",
        "save_template": "Save Template",
        "enter_template_name": "Enter template name:",
        "template_exists": "Template '{name}' exists. Overwrite?",
        "template_saved": "Template '{name}' saved!",
        "template_save_error": "Failed to save template",
        "delete_template": "Delete template '{name}'?",
        "template_deleted": "Template '{name}' deleted",
        "added_template": "Added template '{name}' to timeline",
    },
}

# Settings file path
_settings_dir = Path(os.path.expanduser("~")) / ".fourt"
_settings_file = _settings_dir / "settings.json"


def get_language() -> str:
    """Get current language code"""
    return _current_language


def set_language(lang: str) -> bool:
    """
    Set current language

    Args:
        lang: Language code ('vi' or 'en')

    Returns:
        True if language was changed, False if invalid
    """
    global _current_language

    if lang in _translations:
        _current_language = lang
        _save_language_preference(lang)
        return True
    return False


def get_available_languages() -> list:
    """Get list of available language codes"""
    return list(_translations.keys())


def t(key: str, **kwargs) -> str:
    """
    Translate a key to current language

    Args:
        key: Translation key
        **kwargs: Format arguments for the string

    Returns:
        Translated string, or key if not found
    """
    lang = _current_language

    # Try current language
    if lang in _translations and key in _translations[lang]:
        text = _translations[lang][key]
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
        return text

    # Fallback to Vietnamese
    if "vi" in _translations and key in _translations["vi"]:
        text = _translations["vi"][key]
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
        return text

    # Return key as fallback
    return key


def _(key: str, **kwargs) -> str:
    """Alias for t() function"""
    return t(key, **kwargs)


def load_language_preference():
    """Load saved language preference from settings"""
    global _current_language

    try:
        if _settings_file.exists():
            with open(_settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
                lang = settings.get("language", "vi")
                if lang in _translations:
                    _current_language = lang
    except Exception:
        pass


def _save_language_preference(lang: str):
    """Save language preference to settings"""
    try:
        # Ensure directory exists
        _settings_dir.mkdir(parents=True, exist_ok=True)

        # Load existing settings or create new
        settings = {}
        if _settings_file.exists():
            try:
                with open(_settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except:
                pass

        # Update language
        settings["language"] = lang

        # Save
        with open(_settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def add_translations(lang: str, translations: Dict[str, str]):
    """
    Add or update translations for a language

    Args:
        lang: Language code
        translations: Dictionary of key-value translations
    """
    if lang not in _translations:
        _translations[lang] = {}
    _translations[lang].update(translations)


# Load preference on import
load_language_preference()
