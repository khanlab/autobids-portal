import React from "react";

import Accordion from "./Accordion";
import DirItem from "./DirItem";
import TextItem from "./TextItem";

function genAccordion(fileTree) {
  const textItems = fileTree.files.map((fileName) => (
    <TextItem key={fileName} text={fileName}></TextItem>
  ));
  textItems.sort((a, b) => a.text < b.text ? -1 : 1);
  const dirItems = Object.entries(fileTree.dirs).map(([key, value]) =>
    genDirItem(key, value)
  );
  dirItems.sort((a, b) => a.text < b.text ? -1 : 1);
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
  textItems.sort((a, b) => a.text < b.text ? -1 : 1);
  const dirItems = Object.entries(dirContents.dirs).map(([key, value]) =>
    genDirItem(key, value)
  );
  dirItems.sort((a, b) => a.text < b.text ? -1 : 1);
  return (
    <DirItem text={dirName} key={dirName} dirId={"dir" + dirName.replaceAll("/", "")}>
      {textItems}
      {dirItems}
    </DirItem>
  );
}

export default genAccordion;
