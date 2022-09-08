import { Accordion, TextItem, DirItem, genAccordion } from "./Accordion";
import { TableLauncher, TableLauncherRow } from "./TableLauncher";
import { TaskList, TaskListItem } from "./TaskList";
import ReactDOM from "react-dom";
import React from "react";

globalThis.Accordion = Accordion;
globalThis.TextItem = TextItem;
globalThis.DirItem = DirItem;
globalThis.genAccordion = genAccordion;
globalThis.TableLauncher = TableLauncher;
globalThis.TableLauncherRow = TableLauncherRow;
globalThis.TaskList = TaskList;
globalThis.TaskListItem = TaskListItem;
globalThis.ReactDOM = ReactDOM;
globalThis.React = React;

export {
  Accordion,
  TextItem,
  DirItem,
  genAccordion,
  TableLauncher,
  TableLauncherRow,
  TaskList,
  TaskListItem,
  ReactDOM,
  React,
};
export default {
  Accordion,
  TextItem,
  DirItem,
  genAccordion,
  TableLauncher,
  TableLauncherRow,
  TaskList,
  TaskListItem,
  ReactDOM,
  React,
};
