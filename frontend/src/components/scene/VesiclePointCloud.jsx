import { useLayoutEffect, useRef } from "react";
import { Float32BufferAttribute } from "three";

export default function VesiclePointCloud({
  positions,
  colors,
  pointSize,
}) {
  const geometryRef = useRef(null);

  useLayoutEffect(() => {
    const geometry = geometryRef.current;
    if (!geometry) {
      return;
    }
    geometry.setAttribute("position", new Float32BufferAttribute(positions, 3));
    geometry.setAttribute("color", new Float32BufferAttribute(colors, 3));
    geometry.computeBoundingSphere();
  }, [colors, positions]);

  return (
    <points frustumCulled={false}>
      <bufferGeometry ref={geometryRef} />
      <pointsMaterial
        size={pointSize}
        sizeAttenuation
        vertexColors
        transparent
        opacity={0.72}
        depthWrite={false}
      />
    </points>
  );
}
