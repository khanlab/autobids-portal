import React from "react";
import PropTypes from "prop-types";

import TaskListItem from "./TaskListItem";

function TaskList(props) {
  const { children } = props;

  return (
    <div className="table-responsive" style={{ maxHeight: "400px" }}>
      <table className="table table-light overflow-auto">
        <thead>
          <tr>
            <th scope="col">Start Date and Time</th>
            <th scope="col">End Date and Time</th>
            <th scope="col">Completion Status</th>
            <th scope="col"></th>
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

TaskList.propTypes = {
  children: PropTypes.arrayOf(PropTypes.instanceOf(TaskListItem)),
};

export default TaskList;
