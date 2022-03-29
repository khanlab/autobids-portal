import React from "react";
import PropTypes from "prop-types";

function TableLauncherRow(props) {
  const { id, fileName, date, isActive, deleteUrl, updateActive } = props;

  return (
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
      <td>{fileName}</td>
      <td>{date || "None"}</td>
      <td className="col-md-4">
        <a className="btn btn-danger" href={deleteUrl} role="button">
          Delete
        </a>
      </td>
    </tr>
  );
}

TableLauncherRow.propTypes = {
  id: PropTypes.string.isRequired,
  fileName: PropTypes.string.isRequired,
  date: PropTypes.string,
  isActive: PropTypes.bool.isRequired,
  deleteUrl: PropTypes.string.isRequired,
  updateActive: PropTypes.func.isRequired,
};

export default TableLauncherRow;
