import React from "react";
import PropTypes from "prop-types";

import TextItem from "./TextItem"
import DirItem from "./DirItem"

function Accordion(props) {
  const { children } = props;
  return <ul className="list-group">{children}</ul>;
}

Accordion.propTypes = {
  children: PropTypes.arrayOf(
    PropTypes.oneOfType([
      PropTypes.instanceOf(TextItem),
      PropTypes.instanceOf(DirItem),
    ])
  ).isRequired,
};

export default Accordion;
