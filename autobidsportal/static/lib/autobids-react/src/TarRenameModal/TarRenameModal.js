import React from "react";
import * as ReactDOM from "react-dom";

function TarRenameModal(props) {
  const { fileName, actionUrl } = props;

  return ReactDOM.createPortal(
    <>
      <div className="modal-header">
        <h5 className="modal-title">Rename tar file</h5>
        <button
          type="button"
          className="btn-close"
          data-bs-dismiss="modal"
          aria-label="Close"
        ></button>
      </div>
      <form
        method="post"
        action={actionUrl}
      >
        <div className="modal-body">
          <p>
            You&apos;re about to rename a tar file. This file&apos;s current
            name is: <strong>{fileName}</strong>
          </p>
          <label htmlFor="newTarFileNameInput" className="form-label">
            New tar file name
          </label>
          <input
            className="w-100 form-control"
            type="text"
            name="new_name"
            id="newTarFileNameInput"
            defaultValue={fileName}
          ></input>
        </div>
        <div className="modal-footer">
          <button type="submit" className="btn btn-primary">
            Update tar file name
          </button>
        </div>
      </form>
    </>,
    document.querySelector("#autobidsModalContent")
  );
}

export default TarRenameModal;
