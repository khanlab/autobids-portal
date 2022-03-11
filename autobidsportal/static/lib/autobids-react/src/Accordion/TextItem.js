import React from "react";
import PropTypes from "prop-types";

function TextItem(props) {
  const { text } = props;
  return <li className="list-group-item">{text}</li>;
}

TextItem.propTypes = {
  text: PropTypes.string.isRequired,
};

export default TextItem;
