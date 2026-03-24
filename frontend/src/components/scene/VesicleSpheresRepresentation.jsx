import { useLayoutEffect, useMemo, useRef } from "react";
import { Color, Object3D } from "three";

export default function VesicleSpheresRepresentation({
  positions,
  colors,
  sphereRadius,
  sphereSegments = 10,
}) {
  const meshRef = useRef(null);
  const helperObjectRef = useRef(new Object3D());
  const helperColorRef = useRef(new Color());

  const pointCount = useMemo(() => positions.length / 3, [positions.length]);

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) {
      return;
    }
    const helper = helperObjectRef.current;
    const color = helperColorRef.current;
    mesh.count = pointCount;
    for (let index = 0; index < pointCount; index += 1) {
      const offset = index * 3;
      helper.position.set(
        positions[offset],
        positions[offset + 1],
        positions[offset + 2],
      );
      helper.rotation.set(0, 0, 0);
      helper.scale.setScalar(sphereRadius);
      helper.updateMatrix();
      mesh.setMatrixAt(index, helper.matrix);

      color.setRGB(colors[offset], colors[offset + 1], colors[offset + 2]);
      mesh.setColorAt(index, color);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) {
      mesh.instanceColor.needsUpdate = true;
    }
  }, [colors, pointCount, positions, sphereRadius]);

  return (
    <instancedMesh ref={meshRef} args={[null, null, pointCount]} frustumCulled={false}>
      <sphereGeometry args={[1, sphereSegments, sphereSegments]} />
      <meshStandardMaterial roughness={0.4} metalness={0.05} vertexColors />
    </instancedMesh>
  );
}
