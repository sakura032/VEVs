import { useEffect, useMemo, useRef } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";

import EmptyState from "../../../shared/components/common/EmptyState";
import VesiclePointCloud from "./VesiclePointCloud";
import VesicleSpheresRepresentation from "./VesicleSpheresRepresentation";

function computeDiagonal(bounds) {
  if (!bounds) {
    return 1;
  }
  const dx = bounds.maxX - bounds.minX;
  const dy = bounds.maxY - bounds.minY;
  const dz = bounds.maxZ - bounds.minZ;
  const diagonal = Math.sqrt(dx * dx + dy * dy + dz * dz);
  return Number.isFinite(diagonal) && diagonal > 0 ? diagonal : 1;
}

function CameraResetController({
  resetToken,
  structureCenter,
  structureBounds,
  controlsRef,
}) {
  const { camera } = useThree();

  useEffect(() => {
    if (!structureCenter || !structureBounds || !controlsRef.current) {
      return;
    }
    const diagonal = computeDiagonal(structureBounds);
    const radius = Math.max(diagonal * 0.5, 1.5);
    const fovRadians = (camera.fov * Math.PI) / 180;
    const distance = (radius / Math.sin(fovRadians / 2)) * 1.2;

    camera.position.set(
      structureCenter.x + distance,
      structureCenter.y + distance * 0.55,
      structureCenter.z + distance,
    );
    controlsRef.current.target.set(
      structureCenter.x,
      structureCenter.y,
      structureCenter.z,
    );
    controlsRef.current.update();
  }, [camera, controlsRef, resetToken, structureBounds, structureCenter]);

  return null;
}

export default function VesicleExplorerCanvas({
  renderPayload,
  cameraResetToken,
}) {
  const orbitControlsRef = useRef(null);

  const sceneBounds = renderPayload?.bounds ?? null;
  const sceneCenter = renderPayload?.center ?? null;
  const pointCount = renderPayload?.count ?? 0;

  const lights = useMemo(
    () => ({
      ambient: 1.35,
      key: 2.2,
      fill: 1.0,
    }),
    [],
  );

  if (!renderPayload || pointCount === 0) {
    return (
      <EmptyState
        title="No Vesicle Geometry"
        message="Current filters remove every bead. Relax the residue, leaflet, or clip controls."
      />
    );
  }

  return (
    <div className="molecular-canvas">
      <Canvas camera={{ fov: 35, near: 0.1, far: 2000 }}>
        <color attach="background" args={["#07111b"]} />
        <ambientLight intensity={lights.ambient} />
        <directionalLight position={[120, 140, 80]} intensity={lights.key} />
        <directionalLight position={[-120, -40, -100]} intensity={lights.fill} />

        <CameraResetController
          resetToken={cameraResetToken}
          structureCenter={sceneCenter}
          structureBounds={sceneBounds}
          controlsRef={orbitControlsRef}
        />

        {renderPayload.effectiveDisplayMode === "spheres" ? (
          <VesicleSpheresRepresentation
            positions={renderPayload.positions}
            colors={renderPayload.colors}
            sphereRadius={renderPayload.sphereRadius}
            sphereSegments={10}
          />
        ) : (
          <VesiclePointCloud
            positions={renderPayload.positions}
            colors={renderPayload.colors}
            pointSize={renderPayload.pointSize}
          />
        )}

        <OrbitControls
          ref={orbitControlsRef}
          enableDamping
          dampingFactor={0.08}
          screenSpacePanning={false}
        />
      </Canvas>
    </div>
  );
}
