use base64::{engine::general_purpose, Engine as _};
use image::GenericImageView;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use tauri::Manager;

// ── 配置持久化 ──────────────────────────────────────────────────
#[derive(Serialize, Deserialize, Default)]
struct Config {
    last_export_path: String,
}

fn config_path(app: &tauri::AppHandle) -> PathBuf {
    app.path()
        .app_data_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join("config.json")
}

fn load_config(app: &tauri::AppHandle) -> Config {
    let p = config_path(app);
    fs::read_to_string(&p)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

fn save_config(app: &tauri::AppHandle, cfg: &Config) {
    let p = config_path(app);
    if let Some(dir) = p.parent() {
        let _ = fs::create_dir_all(dir);
    }
    let _ = fs::write(&p, serde_json::to_string(cfg).unwrap_or_default());
}

// ── IPC 命令 ──────────────────────────────────────────────────

/// 读取图片为 base64 data-url
#[tauri::command]
fn read_image_base64(file_path: String) -> Result<String, String> {
    let bytes = fs::read(&file_path).map_err(|e| e.to_string())?;
    let ext = Path::new(&file_path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("png")
        .to_lowercase();
    let mime = match ext.as_str() {
        "jpg" | "jpeg" => "image/jpeg",
        "webp" => "image/webp",
        "gif" => "image/gif",
        _ => "image/png",
    };
    let b64 = general_purpose::STANDARD.encode(&bytes);
    Ok(format!("data:{mime};base64,{b64}"))
}

/// 获取图片宽高元数据
#[derive(Serialize)]
struct ImageMeta {
    width: u32,
    height: u32,
}

#[tauri::command]
fn get_image_meta(file_path: String) -> Result<ImageMeta, String> {
    let img = image::open(&file_path).map_err(|e| e.to_string())?;
    let (width, height) = img.dimensions();
    Ok(ImageMeta { width, height })
}

/// 获取上次导出路径
#[tauri::command]
fn get_last_export_path(app: tauri::AppHandle) -> String {
    load_config(&app).last_export_path
}

/// 保存导出路径
#[tauri::command]
fn save_export_path(app: tauri::AppHandle, dir: String) {
    let mut cfg = load_config(&app);
    cfg.last_export_path = dir;
    save_config(&app, &cfg);
}

/// 裁切参数
#[derive(Deserialize)]
pub struct CutOptions {
    file_path: String,
    cols: u32,
    rows: u32,
    export_dir: String,
}

/// 执行裁切导出，返回输出文件路径列表
#[tauri::command]
fn cut_and_export(opts: CutOptions) -> Result<Vec<String>, String> {
    let img = image::open(&opts.file_path).map_err(|e| e.to_string())?;
    let (width, height) = img.dimensions();

    let cell_w = width / opts.cols;
    let cell_h = height / opts.rows;

    let base_name = Path::new(&opts.file_path)
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("image");
    let ext = Path::new(&opts.file_path)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("png")
        .to_lowercase();

    fs::create_dir_all(&opts.export_dir).map_err(|e| e.to_string())?;

    let mut results = Vec::new();
    let mut index = 1u32;

    for row in 0..opts.rows {
        for col in 0..opts.cols {
            let left = col * cell_w;
            let top = row * cell_h;
            // 最后一格补满剩余像素，避免取整丢像素
            let w = if col == opts.cols - 1 { width - left } else { cell_w };
            let h = if row == opts.rows - 1 { height - top } else { cell_h };

            let cropped = img.crop_imm(left, top, w, h);
            let out_name = format!("{}_{}.{}", base_name, index, ext);
            let out_path = PathBuf::from(&opts.export_dir).join(&out_name);
            cropped
                .save(&out_path)
                .map_err(|e| e.to_string())?;
            results.push(out_path.to_string_lossy().to_string());
            index += 1;
        }
    }

    Ok(results)
}

// ── App 入口 ───────────────────────────────────────────────────
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            read_image_base64,
            get_image_meta,
            get_last_export_path,
            save_export_path,
            cut_and_export,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}