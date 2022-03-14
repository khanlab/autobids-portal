import { Accordion, TextItem, DirItem, genAccordion } from "./Accordion";
import ReactDOM from 'react-dom';

globalThis.Accordion = Accordion;
globalThis.TextItem = TextItem;
globalThis.DirItem = DirItem;
globalThis.genAccordion = genAccordion;
globalThis.ReactDOM = ReactDOM;

export { Accordion, TextItem, DirItem, genAccordion, ReactDOM };
export default { Accordion, TextItem, DirItem, genAccordion, ReactDOM };
