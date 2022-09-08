import React, { useState } from "react";
import PropTypes from "prop-types";

import TaskLogModal from "./TaskLogModal";

function TaskListItem(props) {
  const { start, end, complete, log } = props;

  const [modalOpen, setModalOpen] = useState(false);

  const modalElement = document.getElementById("autobidsModal");
  const openModal = () => setModalOpen(true);
  modalElement.addEventListener("hidden.bs.modal", (event) =>
    setModalOpen(false)
  );

  return (
    <>
      <tr>
        <td>{start}</td>
        <td>{end}</td>
        <td>{complete}</td>
        <td>
          <button
            className="btn btn-primary btn-sm"
            type="button"
            onClick={openModal}
            data-bs-toggle="modal"
            data-bs-target="#autobidsModal"
            disabled={!log}
          >
            View log
          </button>
        </td>
      </tr>
      {modalOpen ? <TaskLogModal log={log} /> : null}
    </>
  );
}

TaskListItem.propTypes = {
  start: PropTypes.string.isRequired,
  end: PropTypes.string.isRequired,
  complete: PropTypes.string.isRequired,
  log: PropTypes.string,
};

export default TaskListItem;
