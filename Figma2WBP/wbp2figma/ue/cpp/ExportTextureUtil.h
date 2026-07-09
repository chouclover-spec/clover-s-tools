// ExportTextureUtil.h
// 暴露给 UE Python 的纹理导出工具: UTexture2D → PNG。
// 编译进项目任意一个 Editor 模块 (或新建 wbp2figma_editor 模块)。
// 用法 (Python):
//   unreal.ExportTextureUtil.export_to_png(texture, r"D:/out/tex.png")
#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "ExportTextureUtil.generated.h"

class UTexture2D;

UCLASS(BlueprintType)
class WBP2FIGMAEDITOR_API UExportTextureUtil : public UObject
{
    GENERATED_BODY()

public:
    // 把 UTexture2D 的源像素导出为 PNG 文件。
    // @param Texture  目标纹理 (建议已勾选 CompressionSettings=TC_VectorDisplacementmap 或读取 Mip0)
    // @param FilePath 输出绝对路径, 如 "D:/Out/Tex.png"
    // @return 是否成功
    UFUNCTION(BlueprintCallable, Category = "wbp2figma")
    static bool ExportToPng(UTexture2D* Texture, const FString& FilePath);

    // 批量导出, 返回成功数量 (Python 里也可以循环调单个版本)
    UFUNCTION(BlueprintCallable, Category = "wbp2figma")
    static int32 ExportManyToPng(const TArray<UTexture2D*>& Textures, const FString& DirPath);
};
