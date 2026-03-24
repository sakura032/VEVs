import StructureExplorerPage from "../pages/StructureExplorerPage";
import WholeVesicleExplorerPage from "../pages/WholeVesicleExplorerPage";

export const appRoutes = [
  {
    id: "whole-vesicle-explorer",
    label: "Whole Vesicle Explorer",
    element: WholeVesicleExplorerPage,
  },
  {
    id: "structure-explorer",
    label: "Structure Explorer",
    element: StructureExplorerPage,
  },
];
