// Copyright (c) 2026 Kurorekishi (EmbarrassingMoment).

#include "WidgetTransitionEffect.h"
#include "TransitionPreset.h"
#include "TransitionMaterialParamUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Widgets/Images/SImage.h"
#include "TransitionFXConfig.h"
#include "TransitionFX.h"

/**
 * Creates or reuses a dynamic material instance and adds a full-screen SImage to
 * the viewport overlay. Validates the preset's widget material and checks for the
 * required "Progress" parameter.
 */
void UWidgetTransitionEffect::Initialize(UWorld* World, UTransitionPreset* Preset)
{
	if (!World || !Preset)
	{
		return;
	}

	UMaterialInterface* SourceMaterial = Preset->WidgetTransitionMaterial;
	if (!SourceMaterial)
	{
		// A PostProcess-domain material will not render in a Slate brush, but fall
		// back anyway so a UI-domain material assigned to the main slot still works.
		SourceMaterial = Preset->TransitionMaterial;
		if (SourceMaterial)
		{
			UE_LOG(LogTransitionFX, Warning, TEXT("WidgetTransitionEffect: WidgetTransitionMaterial is null in Preset %s. Falling back to TransitionMaterial '%s' — WidgetLayer mode requires a User Interface domain material."), *Preset->GetName(), *SourceMaterial->GetName());
		}
	}

	if (!SourceMaterial)
	{
		UE_LOG(LogTransitionFX, Warning, TEXT("WidgetTransitionEffect: No material set in Preset %s"), *Preset->GetName());
		return;
	}

	UGameViewportClient* ViewportClient = World->GetGameViewport();
	if (!ViewportClient)
	{
		UE_LOG(LogTransitionFX, Warning, TEXT("WidgetTransitionEffect: World '%s' has no game viewport. Transition will not be visible."), *World->GetName());
		return;
	}

	// Create or Reuse Dynamic Material
	if (DynamicMaterial && DynamicMaterial->Parent == SourceMaterial)
	{
		DynamicMaterial->ClearParameterValues();
	}
	else
	{
		DynamicMaterial = UKismetMaterialLibrary::CreateDynamicMaterialInstance(World, SourceMaterial);
	}

	if (!DynamicMaterial)
	{
		UE_LOG(LogTransitionFX, Error, TEXT("WidgetTransitionEffect: Failed to create Dynamic Material Instance"));
		return;
	}

	// Check for "Progress" Parameter
	float TempVal = 0.0f;
	static const FMaterialParameterInfo ProgressInfo(TransitionFXConfig::ProgressParamName);
	if (!DynamicMaterial->GetScalarParameterValue(ProgressInfo, TempVal))
	{
		UE_LOG(LogTransitionFX, Error, TEXT("TransitionFX: Material '%s' is missing 'Progress' parameter. Transition will not animate."), *SourceMaterial->GetName());
		DynamicMaterial = nullptr;
		return;
	}

	WidgetBrush.SetResourceObject(DynamicMaterial);

	// Drop a stale widget that was added to a different (old) viewport
	if (OverlayWidget.IsValid() && OwningViewportClient.Get() != ViewportClient)
	{
		RemoveOverlayWidget();
	}

	// Reuse or Create Overlay Widget
	if (!OverlayWidget.IsValid())
	{
		OverlayWidget = SNew(SImage)
			.Image(&WidgetBrush)
			.Visibility(EVisibility::HitTestInvisible);

		// Priority doubles as the overlay Z-order in WidgetLayer mode. The default
		// (1000) sits far above typical UMG AddToViewport Z-orders.
		ViewportClient->AddViewportWidgetContent(OverlayWidget.ToSharedRef(), FMath::RoundToInt32(Preset->Priority));
		OwningViewportClient = ViewportClient;
	}
}

/** Sets the Progress scalar parameter on the dynamic material and invokes the virtual extension point. */
void UWidgetTransitionEffect::UpdateProgress(float Progress)
{
	if (DynamicMaterial)
	{
		DynamicMaterial->SetScalarParameterValue(TransitionFXConfig::ProgressParamName, Progress);
		UpdateMaterialParameters(DynamicMaterial, Progress);
	}
}

/** Removes the overlay widget to hide the effect. The pooled effect object is kept for reuse. */
void UWidgetTransitionEffect::Cleanup()
{
	RemoveOverlayWidget();
	WidgetBrush.SetResourceObject(nullptr);
	DynamicMaterial = nullptr;
}

/** Sets the Invert material parameter. The material uses an If node with a 0.5 threshold. */
void UWidgetTransitionEffect::SetInvert(bool bInvert)
{
	if (DynamicMaterial)
	{
		// Pass 1.0 for True, 0.0 for False.
		// The material will use an "If" node with a threshold of 0.5 to switch logic.
		DynamicMaterial->SetScalarParameterValue(TransitionFXConfig::InvertParamName, bInvert ? 1.0f : 0.0f);
	}
}

/** Applies runtime parameter overrides (scalar, vector, texture) to the dynamic material instance. */
void UWidgetTransitionEffect::SetParameters(const FTransitionParameters& Params)
{
	TransitionFXMaterialUtils::ApplyParameterOverrides(DynamicMaterial, Params);
}

/** Virtual extension point for subclasses to apply additional material parameters each frame. */
void UWidgetTransitionEffect::UpdateMaterialParameters(UMaterialInstanceDynamic* MID, float Progress)
{
	// Base implementation does nothing. Subclasses can override.
}

/** The widget references WidgetBrush by pointer, so it must not outlive this object. */
void UWidgetTransitionEffect::BeginDestroy()
{
	RemoveOverlayWidget();
	Super::BeginDestroy();
}

void UWidgetTransitionEffect::RemoveOverlayWidget()
{
	if (OverlayWidget.IsValid())
	{
		if (UGameViewportClient* ViewportClient = OwningViewportClient.Get())
		{
			ViewportClient->RemoveViewportWidgetContent(OverlayWidget.ToSharedRef());
		}
		OverlayWidget.Reset();
	}
	OwningViewportClient = nullptr;
}
