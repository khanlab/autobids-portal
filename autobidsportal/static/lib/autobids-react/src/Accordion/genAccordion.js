import React from "react";

import Accordion from "./Accordion";
import DirItem from "./DirItem";
import TextItem from "./TextItem";

function sortItems(a, b) {
  return (a.props.text < b.props.text ? -1 : 1);
}

function genAccordion(fileTree) {
  const textItems = fileTree.files.map((fileName) => (
    <TextItem key={fileName} text={fileName}></TextItem>
  ));
  textItems.sort(sortItems);
  const dirItems = Object.entries(fileTree.dirs).map(([key, value]) =>
    genDirItem(key, value)
  );
  dirItems.sort(sortItems);
  return (
    <Accordion>
      {textItems}
      {dirItems}
    </Accordion>
  );
}

function genDirItem(dirName, dirContents) {
  const textItems = dirContents.files.map((fileName) => (
    <TextItem key={fileName} text={fileName}></TextItem>
  ));
  textItems.sort(sortItems);
  const dirItems = Object.entries(dirContents.dirs).map(([key, value]) =>
    genDirItem(key, value)
  );
  dirItems.sort(sortItems);
  return (
    <DirItem text={dirName} key={dirName} dirId={"dir" + dirName.replaceAll("/", "")}>
      {textItems}
      {dirItems}
    </DirItem>
  );
}

export default genAccordion;
