// Copyright (c) 2026 Kurorekishi (EmbarrassingMoment).

#include "TransitionPreset.h"
#include "PostProcessTransitionEffect.h"
#include "WidgetTransitionEffect.h"

UClass* UTransitionPreset::GetEffectiveEffectClass() const
{
	// WidgetLayer mode only substitutes the stock PostProcess effect class.
	// A custom EffectClass (including Blueprint subclasses) always wins.
	if (RenderingMode == ETransitionRenderingMode::WidgetLayer
		&& (!EffectClass || EffectClass == UPostProcessTransitionEffect::StaticClass()))
	{
		return UWidgetTransitionEffect::StaticClass();
	}

	return EffectClass;
}
