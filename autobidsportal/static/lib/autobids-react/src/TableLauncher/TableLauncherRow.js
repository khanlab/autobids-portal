import React, { useState } from "react";
import PropTypes from "prop-types";

import { TarRenameModal } from "../TarRenameModal";

function TableLauncherRow(props) {
  const {
    id,
    fileName,
    date,
    isActive,
    deleteUrl,
    renameUrl,
    updateActive,
    mutable,
  } = props;

  const [modalOpen, setModalOpen] = useState(false);

  const modalElement = document.getElementById("autobidsModal");
  const openModal = () => {
    setModalOpen(true);
  };
  modalElement.addEventListener("hidden.bs.modal", (event) =>
    setModalOpen(false)
  );

  return (
    <>
      <tr>
        <td>
          <div className="form-check">
            <input
              className="form-check-input"
              type="checkbox"
              value={id}
              id={id}
              name="tar_files"
              checked={isActive}
              onChange={() => updateActive(id, !isActive)}
            />
            <label className="form-check-label" htmlFor={id}>
              Yes
            </label>
          </div>
        </td>
        <td>
          <code>{fileName}</code>
          <button
            className="btn btn-primary btn-sm"
            type="button"
            onClick={openModal}
            data-bs-toggle="modal"
            data-bs-target="#autobidsModal"
            disabled={!mutable}
          >
            Rename
          </button>
        </td>
        <td>{date || "None"}</td>
        <td className="col-md-4">
          <a className="btn btn-danger" href={deleteUrl} role="button">
            Delete
          </a>
        </td>
      </tr>
      {modalOpen ? (
        <TarRenameModal fileName={fileName} actionUrl={renameUrl} />
      ) : null}
    </>
  );
}

TableLauncherRow.propTypes = {
  id: PropTypes.string.isRequired,
  fileName: PropTypes.string.isRequired,
  date: PropTypes.string,
  isActive: PropTypes.bool.isRequired,
  deleteUrl: PropTypes.string.isRequired,
  renameUrl: PropTypes.string.isRequired,
  updateActive: PropTypes.func.isRequired,
  mutable: PropTypes.bool,
};

export default TableLauncherRow;
