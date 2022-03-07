import React from "react";
import ReactDOM from "react-dom";
import Accordion from "./accordion/Accordion";
import TextItem from "./accordion/TextItem";
import DirItem from "./accordion/DirItem";

ReactDOM.render(
  <React.StrictMode>
    <Accordion>
      <TextItem text="dataset-description.json" />
      <DirItem text="sub-01" dirId="dirsub01">
        <DirItem text="anat" dirId="diranat">
          <TextItem text="sub-01_t1w.nii.gz" />
        </DirItem>
      </DirItem>
    </Accordion>
  </React.StrictMode>,
  document.getElementById("root")
);
