// Copyright (c) 2026 Kurorekishi (EmbarrassingMoment).

#pragma once

#include "CoreMinimal.h"

class UMaterialInstanceDynamic;
struct FTransitionParameters;

namespace TransitionFXMaterialUtils
{
	/**
	 * Applies runtime parameter overrides (scalar, vector, texture) to a dynamic
	 * material instance. Logs a warning for each override that targets a parameter
	 * the material does not expose, instead of silently ignoring it.
	 * Shared by the PostProcess and WidgetLayer effect implementations.
	 */
	void ApplyParameterOverrides(UMaterialInstanceDynamic* MID, const FTransitionParameters& Params);
}
