import React from "react";
import PropTypes from "prop-types";

import TextItem from "./TextItem"

function DirItem(props) {
  const { text, children, dirId } = props;
  return (
    <li className="list-group-item">
      <button
        className="btn btn-link"
        type="button"
        data-bs-toggle="collapse"
        data-bs-target={`#${dirId}`}
        aria-expanded="false"
      >
        {text}
      </button>
      <ul className="list-group collapse" id={dirId}>
        {children}
      </ul>
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
