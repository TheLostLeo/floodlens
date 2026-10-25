import path from 'node:path';
import { pathToFileURL } from 'node:url';
const root='A:/projects/floodlens';
const skill='C:/Users/thelo/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations';
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({
  workspaceDir:root,
  candidatePath:path.join(root,'.codex-build/floodlens-presentation/FloodLens-Final-Project-Report-draft.pptx'),
  finalPath:path.join(root,'deliverables/FloodLens-Final-Project-Report-20-Slides-Team.pptx'),
  pythonExecutable:'C:/Users/thelo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
  integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
  explicitTotalSlideCount:20,
  requiredNativeTableOwnerSlides:[],
  requiredNativeChartOwnerSlides:[14],
  materializeLiteralChartWorkbooks:true,
  fontPolicy:{basis:'design',families:['Aptos']},
  verifyArtifactToolImport:true,
  receiptPath:path.join(root,'.codex-build/floodlens-presentation/FloodLens-Final-Project-Report-20-Slides-Team.validation.json')
});
console.log(JSON.stringify(result,null,2));
