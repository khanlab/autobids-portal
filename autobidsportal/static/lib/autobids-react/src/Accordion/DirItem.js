import React, { useState } from "react";
import PropTypes from "prop-types";
import Button from "react-bootstrap/Button";
import Collapse from "react-bootstrap/Collapse";

import TextItem from "./TextItem"

function DirItem(props) {
  const { text, children, dirId } = props;
  const [open, setOpen] = useState(false);
  return (
    <li className="list-group-item">
      <Button
        onClick={() => setOpen(!open)}
        aria-controls={dirId}
        aria-expanded={open}
        variant="link"
      >
        {text}
      </Button>
      <Collapse in={open}>
          <ul className="list-group collapse" id={dirId}>
            {children}
          </ul>
      </Collapse>
    </li>
  );
}

DirItem.propTypes = {
  text: PropTypes.string.isRequired,
  children: PropTypes.arrayOf(
    PropTypes.oneOfType([
      PropTypes.instanceOf(TextItem),
      PropTypes.instanceOf(DirItem),
    ])
  ).isRequired,
  dirId: PropTypes.string.isRequired,
};

export default DirItem;
