// Copyright (c) 2026 Kurorekishi (EmbarrassingMoment).

#pragma once

#include "CoreMinimal.h"
#include "TransitionFXTypes.generated.h"

/**
 * Rendering path used to draw a transition.
 */
UENUM(BlueprintType)
enum class ETransitionRenderingMode : uint8
{
	/** PostProcess volume + blendable material (default). Does not cover UMG/Slate UI layers. */
	PostProcess UMETA(DisplayName = "Post Process"),

	/** Full-screen Slate widget on the viewport overlay. Also covers UMG widgets added to the viewport. Requires a User Interface domain material. */
	WidgetLayer UMETA(DisplayName = "Widget Layer")
};

/**
 * Procedural easing functions for transitions.
 */
UENUM(BlueprintType)
enum class ETransitionEasing : uint8
{
	Linear UMETA(DisplayName = "Linear"),

	EaseInSine UMETA(DisplayName = "Sine In"),
	EaseOutSine UMETA(DisplayName = "Sine Out"),
	EaseInOutSine UMETA(DisplayName = "Sine In/Out"),

	EaseInCubic UMETA(DisplayName = "Cubic In"),
	EaseOutCubic UMETA(DisplayName = "Cubic Out"),
	EaseInOutCubic UMETA(DisplayName = "Cubic In/Out"),

	EaseInExpo UMETA(DisplayName = "Expo In"),
	EaseOutExpo UMETA(DisplayName = "Expo Out"),
	EaseInOutExpo UMETA(DisplayName = "Expo In/Out"),

	EaseOutElastic UMETA(DisplayName = "Elastic Out"),
	EaseOutBounce UMETA(DisplayName = "Bounce Out"),

	Custom UMETA(DisplayName = "Custom Curve")
};
