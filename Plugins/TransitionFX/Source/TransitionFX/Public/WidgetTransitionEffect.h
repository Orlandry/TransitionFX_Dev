// Copyright (c) 2026 Kurorekishi (EmbarrassingMoment).

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "ITransitionEffect.h"
#include "Styling/SlateBrush.h"
#include "WidgetTransitionEffect.generated.h"

class UTransitionPreset;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UGameViewportClient;
class SWidget;

/**
 * Concrete transition effect that draws the transition material as a full-screen
 * Slate widget on the viewport overlay. Unlike UPostProcessTransitionEffect, this
 * also covers UMG widgets added to the viewport. Requires a material with the
 * User Interface domain (UTransitionPreset::WidgetTransitionMaterial).
 */
UCLASS(Blueprintable, BlueprintType)
class TRANSITIONFX_API UWidgetTransitionEffect : public UObject, public ITransitionEffect
{
	GENERATED_BODY()

public:
	// ITransitionEffect Interface

	/** Creates or reuses a dynamic material and adds a full-screen widget to the viewport overlay. */
	virtual void Initialize(UWorld* World, UTransitionPreset* Preset) override;

	/** Updates the material's Progress parameter and calls UpdateMaterialParameters. */
	virtual void UpdateProgress(float Progress) override;

	/** Removes the overlay widget and clears the dynamic material reference. */
	virtual void Cleanup() override;

	/** Sets the material's Invert parameter (1.0 for inverted, 0.0 for normal). */
	virtual void SetInvert(bool bInvert) override;

	/** Applies scalar, vector, and texture parameter overrides to the dynamic material. */
	virtual void SetParameters(const FTransitionParameters& Params) override;

	/**
	 * Updates custom material parameters. Override this in subclasses to add extra parameters.
	 * @param MID The dynamic material instance.
	 * @param Progress The current transition progress.
	 */
	virtual void UpdateMaterialParameters(UMaterialInstanceDynamic* MID, float Progress);

	// UObject Interface

	/** Ensures the overlay widget is removed before the effect object is destroyed. */
	virtual void BeginDestroy() override;

protected:
	/** Removes the overlay widget from its viewport, if present. */
	void RemoveOverlayWidget();

	/** The dynamic material instance created at runtime. */
	UPROPERTY(Transient, BlueprintReadOnly, Category = "TransitionFX")
	TObjectPtr<UMaterialInstanceDynamic> DynamicMaterial;

	/** Brush that feeds the dynamic material into the full-screen widget. The material is kept alive by DynamicMaterial. */
	FSlateBrush WidgetBrush;

	/** The full-screen Slate widget added to the viewport overlay. */
	TSharedPtr<SWidget> OverlayWidget;

	/** The viewport client the widget was added to. Weak so viewport teardown is handled safely. */
	TWeakObjectPtr<UGameViewportClient> OwningViewportClient;
};
