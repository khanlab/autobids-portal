import React from "react";
import * as ReactDOM from "react-dom";
import PropTypes from "prop-types";

function TaskLogModal(props) {
  const { log } = props;

  return ReactDOM.createPortal(
    <>
      <div className="modal-header">
        <h5 className="modal-title">Task log</h5>
        <button
          type="button"
          className="btn-close"
          data-bs-dismiss="modal"
          aria-label="close"
        ></button>
      </div>
      <div className="modal-body">
        <pre>{log}</pre>
      </div>
    </>,
    document.querySelector("#autobidsModalContent")
  );
}

TaskLogModal.propTypes = {
  log: PropTypes.string.isRequired,
};

export default TaskLogModal;
