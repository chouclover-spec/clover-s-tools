// ExportTextureUtil.cpp
// 实现: 读取 UTexture2D 的 Mip0 像素 → PNG。
#include "ExportTextureUtil.h"

#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "Modules/ModuleManager.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "ImageWriteBlueprintLibrary.h"
#include "TextureResource.h"
#include "Engine/Texture2D.h"

// 优先用 UImageWriteBlueprintLibrary (4.25+), API 最稳。
// 4.24 及更早回退到 FImageUtils 手动封装 PNG。
bool UExportTextureUtil::ExportToPng(UTexture2D* Texture, const FString& FilePath)
{
    if (!Texture)
    {
        return false;
    }

#if ENGINE_MAJOR_VERSION >= 5 || (ENGINE_MAJOR_VERSION == 4 && ENGINE_MINOR_VERSION >= 25)
    FString OutPath = FilePath;
    FPaths::MakeStandardFilename(OutPath);
    UImageWriteBlueprintLibrary::ExportToDisk(Texture, OutPath, EImageFormat::PNG);
    return true;
#else
    FTexturePlatformData* PlatformData = Texture->GetPlatformData();
    if (!PlatformData || PlatformData->Mips.Num() == 0)
    {
        return false;
    }
    FTexture2DMipMap& Mip = PlatformData->Mips[0];
    FByteBulkData* RawData = &Mip.BulkData;
    if (!RawData)
    {
        return false;
    }
    void* LockedData = RawData->Lock(LOCK_READ_ONLY);
    if (!LockedData)
    {
        return false;
    }

    int32 SizeX = Mip.SizeX;
    int32 SizeY = Mip.SizeY;
    // 提示: 若纹理为 DXT 压缩, 这里拿到的是压缩块而非 BGRA8。
    // 导出前请把纹理 CompressionSettings 设为 VectorDisplacementmap (无压缩 BGRA8)。
    TArray<uint8> RawBytes;
    RawBytes.Append((uint8*)LockedData, RawData->GetElementCount() * (int32)RawData->GetElementSize());
    RawData->Unlock();

    IImageWrapperModule& ImageWrapperModule = FModuleManager::LoadModuleChecked<IImageWrapperModule>(FName("ImageWrapper"));
    TSharedPtr<IImageWrapper> ImageWrapper = ImageWrapperModule.CreateImageWrapper(EImageFormat::PNG);
    if (!ImageWrapper.IsValid())
    {
        return false;
    }
    if (!ImageWrapper->SetRaw(RawBytes.GetData(), RawBytes.Num(), SizeX, SizeY, ERGBFormat::BGRA, 8))
    {
        return false;
    }
    const TArray64<uint8>& PngBytes = ImageWrapper->GetCompressed();
    return FFileHelper::SaveArrayToFile(PngBytes, *FilePath);
#endif
}

int32 UExportTextureUtil::ExportManyToPng(const TArray<UTexture2D*>& Textures, const FString& DirPath)
{
    int32 Ok = 0;
    for (UTexture2D* Tex : Textures)
    {
        if (!Tex)
        {
            continue;
        }
        FString Path = FPaths::Combine(DirPath, Tex->GetName() + TEXT(".png"));
        if (ExportToPng(Tex, Path))
        {
            ++Ok;
        }
    }
    return Ok;
}
