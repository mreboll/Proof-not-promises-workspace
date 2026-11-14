import React from "react";
import { Composition } from "remotion";
import { Demo } from "./Demo";
import { FPS, H, W } from "./theme";
import { TOTAL_FRAMES } from "./timeline";

export function RemotionRoot() {
  return <Composition id="Demo" component={Demo} durationInFrames={TOTAL_FRAMES} fps={FPS} width={W} height={H} />;
}
